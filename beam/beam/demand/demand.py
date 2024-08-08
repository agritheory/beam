import calendar
import datetime
from collections import deque
from time import localtime
from typing import TYPE_CHECKING, Any, Union

import frappe
from frappe.utils.data import flt, get_datetime
from frappe.utils.nestedset import get_descendants_of

from beam.beam.demand.sqlite import dict_factory, get_demand_db

if TYPE_CHECKING:
	from sqlite3 import Cursor

	from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import PurchaseInvoice
	from erpnext.accounts.doctype.purchase_invoice_item.purchase_invoice_item import (
		PurchaseInvoiceItem,
	)
	from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
	from erpnext.accounts.doctype.sales_invoice_item.sales_invoice_item import SalesInvoiceItem
	from erpnext.stock.doctype.delivery_note.delivery_note import DeliveryNote
	from erpnext.stock.doctype.delivery_note_item.delivery_note_item import DeliveryNoteItem
	from erpnext.stock.doctype.purchase_receipt.purchase_receipt import PurchaseReceipt
	from erpnext.stock.doctype.purchase_receipt_item.purchase_receipt_item import PurchaseReceiptItem
	from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry
	from erpnext.stock.doctype.stock_entry_detail.stock_entry_detail import StockEntryDetail
	from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import StockReconciliation
	from erpnext.stock.doctype.stock_reconciliation_item.stock_reconciliation_item import (
		StockReconciliationItem,
	)


def get_qty_from_sle(item_code: str, warehouse: str | None = None, company: str | None = None):
	if not company and not warehouse:
		company = frappe.defaults.get_defaults().get("company")

	warehouses = []
	if warehouse:
		warehouses = [warehouse]

	if not warehouse or frappe.get_cached_value("Warehouse", warehouse, "is_group"):
		root_warehouse = frappe.get_all(
			"Warehouse",
			{"company": company, "is_group": True, "parent_warehouse": ["is", "not set"]},
			pluck="name",
		)[0]

		warehouses = get_descendant_warehouses(company, root_warehouse)

	balance_qty = frappe.get_all(
		"Stock Ledger Entry",
		filters={"item_code": item_code, "warehouse": ["in", warehouses], "is_cancelled": False},
		fields=["qty_after_transaction", "warehouse"],
		order_by="posting_date desc, posting_time desc, creation desc",
	)

	if not warehouse:
		return balance_qty

	return flt(balance_qty[0].qty_after_transaction) if balance_qty else 0.0


def get_manufacturing_demand() -> list[frappe._dict]:
	manufacturing_demand = []

	pending_work_orders = frappe.get_all(
		"Work Order",
		filters={"docstatus": 1, "status": "Not Started"},
		fields=["name", "company", "wip_warehouse", "planned_start_date"],
		order_by="planned_start_date, creation ASC",
	)

	for work_order in pending_work_orders:
		work_order_items = frappe.get_all(
			"Work Order Item",
			filters={"parent": work_order.name},
			fields=["name", "item_code", "required_qty", "transferred_qty"],
		)

		for item in work_order_items:
			if item.transferred_qty - item.required_qty >= 0:
				continue

			manufacturing_demand.append(
				frappe._dict(
					{
						"doctype": "Work Order",
						"parent": work_order.name,
						"company": work_order.company,
						"warehouse": work_order.wip_warehouse,
						"name": item.name,
						"item_code": item.item_code,
						"delivery_date": work_order.planned_start_date,
						"total_required_qty": item.required_qty - item.transferred_qty,
						"stock_uom": frappe.db.get_value("Item", item.item_code, "stock_uom"),
					}
				)
			)

	return manufacturing_demand


def get_sales_demand() -> list[frappe._dict]:
	sales_demand = []
	default_fg_warehouse = frappe.db.get_single_value(
		"Manufacturing Settings", "default_fg_warehouse"
	)

	sales_orders = frappe.get_all(
		"Sales Order",
		filters={"docstatus": 1, "status": ["!=", "Closed"]},
		fields=["name", "company", "delivery_date"],
		order_by="delivery_date, creation ASC",
	)

	for sales_order in sales_orders:
		sales_order_items = frappe.get_all(
			"Sales Order Item",
			filters={"parent": sales_order.name},
			fields=["name", "item_code", "stock_qty", "delivered_qty"],
		)

		for item in sales_order_items:
			if item.stock_qty - item.delivered_qty <= 0:
				continue

			sales_demand.append(
				frappe._dict(
					{
						"doctype": "Sales Order",
						"parent": sales_order.name,
						"company": sales_order.company,
						"warehouse": default_fg_warehouse,
						"name": item.name,
						"item_code": item.item_code,
						"delivery_date": sales_order.delivery_date,
						"total_required_qty": item.stock_qty - item.delivered_qty,
						"stock_uom": frappe.db.get_value("Item", item.item_code, "stock_uom"),
					}
				)
			)

	return sales_demand


def build_demand_map() -> None:
	manufacturing_demand = get_manufacturing_demand()
	sales_demand = get_sales_demand()

	output = []
	for row in manufacturing_demand + sales_demand:
		row.key = frappe.generate_hash()
		row.delivery_date = str(calendar.timegm(get_datetime(row.delivery_date).timetuple()))
		row.total_required_qty = str(row.total_required_qty)
		output.append(row)

	with get_demand_db() as conn:
		cur = conn.cursor()
		cur.execute("DELETE FROM demand;")  # sqlite does not implement a TRUNCATE command
		cur.execute("DELETE FROM allocation;")  # sqlite does not implement a TRUNCATE command
		for row in output:
			cur.execute(
				f"""INSERT INTO demand ('{"', '".join(row.keys())}') VALUES ('{"', '".join(row.values())}')"""
			)

	build_allocation_map()


def build_allocation_map(
	row: Union[
		"DeliveryNoteItem",
		"PurchaseInvoiceItem",
		"PurchaseReceiptItem",
		"SalesInvoiceItem",
		"StockEntryDetail",
		"StockReconciliationItem",
		None,
	] = None,
	action: dict | None = None,
):
	if row and action:
		update_allocations(row=row, action=action)
	else:
		create_allocations()


def get_demand_query(
	cursor: "Cursor",
	row: Union[
		"DeliveryNoteItem",
		"PurchaseInvoiceItem",
		"PurchaseReceiptItem",
		"SalesInvoiceItem",
		"StockEntryDetail",
		"StockReconciliationItem",
		None,
	] = None,
	action: dict | None = None,
):
	item_query = warehouse_query = ""
	if row:
		item_query = f"WHERE item_code = '{row.item_code}'"
		# TODO: should we only consider warehouse if it is the same as the demand warehouse?
		# if action:
		# 	warehouse_field = action.get("warehouse_field")
		# 	if warehouse_field:
		# 		warehouse_query = f"AND warehouse = '{row.get(warehouse_field)}'"

	return cursor.execute(
		f"""
		SELECT
			d.*,
			COALESCE(
				(SELECT SUM(a.allocated_qty) FROM allocation a WHERE a.demand = d.key),
				0
			) AS allocated_qty,
			d.total_required_qty - COALESCE(
				(SELECT SUM(a.allocated_qty) FROM allocation a WHERE a.demand = d.key),
				0
			) AS net_required_qty
		FROM
			demand d
		{item_query}
		{warehouse_query}
		ORDER BY delivery_date ASC;
		"""
	)


def get_item_demand_map(
	cursor: "Cursor",
	row: Union[
		"DeliveryNoteItem",
		"PurchaseInvoiceItem",
		"PurchaseReceiptItem",
		"SalesInvoiceItem",
		"StockEntryDetail",
		"StockReconciliationItem",
		None,
	] = None,
	action: dict | None = None,
):
	demand_query = get_demand_query(cursor, row=row, action=action)
	demand_rows = demand_query.fetchall()

	item_demand_map = frappe._dict({})
	for demand_row in demand_rows:
		if demand_row.item_code in item_demand_map:
			item_demand_map[demand_row.item_code].append(demand_row)
		else:
			item_demand_map[demand_row.item_code] = [demand_row]

	return item_demand_map


def update_allocations(
	row: Union[
		"DeliveryNoteItem",
		"PurchaseInvoiceItem",
		"PurchaseReceiptItem",
		"SalesInvoiceItem",
		"StockEntryDetail",
		"StockReconciliationItem",
	],
	action: dict,
):
	with get_demand_db() as conn:
		conn.row_factory = dict_factory
		cur = conn.cursor()

		quantity_field = action.get("quantity_field")
		row_qty = row.get(quantity_field) if quantity_field else None

		warehouse_field = action.get("warehouse_field")
		warehouse = row.get(warehouse_field)

		allocation_query = cur.execute(
			f"""
			SELECT
				*
			FROM
				allocation
			WHERE
				item_code = '{row.item_code}'
				AND warehouse = '{warehouse}'
				AND allocated_qty > 0
			"""
		)

		existing_allocations = allocation_query.fetchall()
		if existing_allocations:
			demand_effect = action.get("demand_effect")
			for allocation in existing_allocations:
				demand_query = cur.execute(f"SELECT * FROM demand WHERE key = '{allocation.demand}'")
				demand_row = demand_query.fetchone()

				if demand_effect == "increase":
					new_allocated_qty = min(demand_row.total_required_qty, allocation.allocated_qty + row_qty)
				elif demand_effect == "decrease":
					new_allocated_qty = max(0, allocation.allocated_qty - row_qty)
				elif demand_effect == "adjustment":
					new_allocated_qty = min(demand_row.total_required_qty, row_qty)

				cur.execute(
					f"UPDATE allocation SET allocated_qty = {new_allocated_qty} WHERE key = '{allocation.key}'"
				)
		else:
			item_demand_map = get_item_demand_map(cur, row=row, action=action)
			demand_rows = item_demand_map.get(row.item_code)
			if not demand_rows:
				return
			demand_queue = deque(demand_rows)

			allocations = []
			while demand_queue:
				current_demand = demand_queue[0]
				net_required_qty = current_demand["total_required_qty"] - current_demand["allocated_qty"]
				allocated_qty = min(row_qty, net_required_qty)

				allocations.append(
					{
						**new_allocation(current_demand),
						"warehouse": warehouse,
						"allocated_qty": str(allocated_qty),
					}
				)

				if row_qty >= net_required_qty:
					# Full demand can be met
					demand_queue.popleft()
				else:
					# Partial demand is met
					current_demand["total_required_qty"] -= allocated_qty
					break

			for allocation in allocations:
				cur.execute(
					f"""INSERT INTO allocation ('{"', '".join(allocation.keys())}') VALUES ('{"', '".join(allocation.values())}')"""
				)


def create_allocations():
	with get_demand_db() as conn:
		conn.row_factory = dict_factory
		cur = conn.cursor()

		item_demand_map = get_item_demand_map(cur)

		allocations = []
		for item_code, demand_rows in item_demand_map.items():
			demand_queue = deque(demand_rows)
			supply_queue = deque(get_qty_from_sle(item_code))
			if not any([supply_queue, demand_queue]):
				continue

			while supply_queue and demand_queue:
				current_demand = demand_queue[0]
				current_supply = supply_queue[0]

				net_required_qty = current_demand["total_required_qty"] - current_demand["allocated_qty"]
				allocated_qty = min(current_supply["qty_after_transaction"], net_required_qty)

				allocation = {
					**new_allocation(current_demand),
					"warehouse": current_supply.get("warehouse"),
					"allocated_qty": str(allocated_qty),
				}

				if current_supply["qty_after_transaction"] >= net_required_qty:
					# Full demand can be met
					current_supply["qty_after_transaction"] -= allocated_qty
					demand_queue.popleft()

					if current_supply["qty_after_transaction"] == 0:
						supply_queue.popleft()
						break
				else:
					# Partial demand is met
					current_demand["total_required_qty"] -= allocated_qty
					supply_queue.popleft()

				allocations.append(allocation)

		for allocation in allocations:
			cur.execute(
				f"""INSERT INTO allocation ('{"', '".join(allocation.keys())}') VALUES ('{"', '".join(allocation.values())}')"""
			)


def new_allocation(demand_row):
	return frappe._dict(
		{
			"key": frappe.generate_hash(),
			"demand": demand_row.key,
			"doctype": demand_row.doctype,
			"company": demand_row.company,
			"parent": demand_row.parent,
			"name": demand_row.name,
			"item_code": demand_row.item_code,
			"allocated_date": str(calendar.timegm(get_datetime().timetuple())),
			"modified": str(calendar.timegm(get_datetime().timetuple())),
			"stock_uom": demand_row.stock_uom,
			"status": "Soft Allocated",
			"assigned": demand_row.assigned or "",
		}
	)


def modify_allocations(
	doc: Union[
		"DeliveryNote",
		"PurchaseInvoice",
		"PurchaseReceipt",
		"SalesInvoice",
		"StockEntry",
		"StockReconciliation",
	],
	method: str,
):
	demand_hooks = frappe.get_hooks("demand")
	doctype_matrix: dict[str, list[dict[str, Any]]] = demand_hooks.get(doc.doctype)
	if not doctype_matrix:
		return
	method_matrix = doctype_matrix.get(method)
	if not method_matrix:
		return
	for row in doc.get("items"):
		for action in method_matrix:
			conditions = action.get("conditions")
			if conditions:
				for key, value in conditions.items():
					if doc.get(key) == value:
						build_allocation_map(row=row, action=action)
			else:
				build_allocation_map(row=row, action=action)


def get_descendant_warehouses(company, warehouse) -> list[str]:
	beam_settings = frappe.get_doc("BEAM Settings", company)

	warehouse_types = [wt.warehouse_type for wt in beam_settings.warehouse_types]
	if not warehouse_types:
		return get_descendants_of("Warehouse", warehouse, ignore_permissions=True, order_by="lft")

	order_by = "lft"
	limit = None
	lft, rgt = frappe.get_cached_value("Warehouse", warehouse, ["lft", "rgt"])

	if rgt - lft <= 1:
		return []

	return frappe.get_all(
		"Warehouse",
		filters={
			"lft": [">", lft],
			"rgt": ["<", rgt],
			"company": beam_settings.company,
			"warehouse_type": ["not in", warehouse_types],
		},
		pluck="name",
		order_by=order_by,
		limit_page_length=limit,
	)


@frappe.whitelist()
def get_demand(
	company,
	item_code=None,
	warehouse=None,
	workstation=None,
	assigned=None,
	order_by="workstation, assigned",
):
	filters = {}
	if workstation:
		filters["workstation"] = f"{workstation}"
	if item_code:
		filters["item_code"] = f"{item_code}"
	if warehouse:
		filters["warehouse"] = f"{warehouse}"

	d_filters = "AND " + "\nAND ".join([f"d.{key} IN ('{value}')" for key, value in filters.items()])
	a_filters = "AND " + "\nAND ".join([f"a.{key} IN ('{value}')" for key, value in filters.items()])

	# if assigned:
	# 	_filters += f" AND assigned LIKE %{assigned}%"

	with get_demand_db() as conn:
		conn.row_factory = dict_factory
		cur = conn.cursor()
		query = f"""
			SELECT
				d.key,
				'' AS demand,
				d.doctype,
				d.company,
				d.parent,

				d.warehouse,
				d.name,
				d.item_code,
				d.delivery_date AS allocated_date,
				d.delivery_date,

				d.modified,
				d.stock_uom,
				COALESCE(
					(SELECT SUM(a.allocated_qty) FROM allocation a WHERE a.demand = d.key),
					0
				) AS allocated_qty,
				d.total_required_qty - COALESCE(
					(SELECT SUM(a.allocated_qty) FROM allocation a WHERE a.demand = d.key),
					0
				) AS net_required_qty,
				d.total_required_qty,

				'' AS status,
				d.assigned
			FROM demand d
			WHERE allocated_qty <= 0
			{d_filters}
			UNION ALL
			SELECT
				a.key,
				a.demand,
				a.doctype,
				a.company,
				a.parent,

				a.warehouse,
				a.name,
				a.item_code,
				a.allocated_date AS delivery_date,
				a.allocated_date,

				a.modified,
				a.stock_uom,
				a.allocated_qty,
				COALESCE(
					(SELECT d.total_required_qty FROM demand d WHERE a.demand = d.key),
					0
				) -
				COALESCE(
					(SELECT SUM(c.allocated_qty) FROM allocation c WHERE a.demand = c.demand),
					0
				) AS net_required_qty,
				(SELECT d.total_required_qty FROM demand d WHERE a.demand = d.key) AS total_required_qty,

				a.status,
				a.assigned
			FROM allocation a
			WHERE allocated_qty > 0
			{a_filters}
			ORDER BY delivery_date, parent ASC
		"""
		rows = cur.execute(query).fetchall()

		for row in rows:
			row.delivery_date = datetime.datetime(*localtime(row.delivery_date)[:6])
			row.allocated_date = datetime.datetime(*localtime(row.allocated_date)[:6])
			row.modified = datetime.datetime(*localtime(row.modified)[:6])
		return rows
