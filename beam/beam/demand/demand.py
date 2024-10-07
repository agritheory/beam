# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

from collections import deque
from typing import TYPE_CHECKING, Any, Optional, Union

import frappe
from frappe.query_builder import DocType, Field
from frappe.query_builder.custom import ConstantColumn
from frappe.utils.data import flt
from frappe.utils.nestedset import get_descendants_of

from beam.beam.demand.sqlite import get_demand_db, reset_demand_db
from beam.beam.demand.utils import (
	Allocation,
	Demand,
	get_datetime_from_epoch,
	get_epoch_from_datetime,
)

if TYPE_CHECKING:
	from sqlite3 import Cursor

	from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import PurchaseInvoice
	from erpnext.accounts.doctype.purchase_invoice_item.purchase_invoice_item import (
		PurchaseInvoiceItem,
	)
	from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
	from erpnext.accounts.doctype.sales_invoice_item.sales_invoice_item import SalesInvoiceItem
	from erpnext.manufacturing.doctype.work_order.work_order import WorkOrder
	from erpnext.selling.doctype.sales_order.sales_order import SalesOrder
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
	warehouses = []
	if warehouse:
		warehouses = [warehouse]

	if not warehouse or frappe.get_cached_value("Warehouse", warehouse, "is_group"):
		warehouses = get_demand_warehouses(company)

	balance_qty = frappe.get_all(
		"Stock Ledger Entry",
		filters={"item_code": item_code, "warehouse": ["in", warehouses], "is_cancelled": False},
		fields=["qty_after_transaction", "warehouse"],
		order_by="posting_date desc, posting_time desc, creation DESC",
	)

	if not warehouse:
		return balance_qty

	return flt(balance_qty[0].qty_after_transaction) if balance_qty else 0.0


def get_manufacturing_demand(
	name: str | None = None, item_code: str | None = None
) -> list[Demand]:

	WorkOrder = DocType("Work Order")
	WorkOrderItem = DocType("Work Order Item")
	WorkOrderOperation = DocType("Work Order Operation")
	Item = DocType("Item")

	workstation_subquery = (
		frappe.qb.from_(WorkOrderOperation)
		.select(WorkOrderOperation.workstation)
		.where(WorkOrderOperation.parent == WorkOrder.name)
		.orderby(WorkOrderOperation.idx)
		.limit(1)
	)

	total_required_qty = Field("required_qty") - Field("transferred_qty")

	work_order_query = (
		frappe.qb.from_(WorkOrder)
		.join(WorkOrderItem)
		.on(WorkOrder.name == WorkOrderItem.parent)
		.left_join(Item)
		.on(Item.item_code == WorkOrderItem.item_code)
		.select(
			ConstantColumn("Work Order").as_("doctype"),
			WorkOrder.name.as_("parent"),
			WorkOrder.company,
			WorkOrder.wip_warehouse.as_("warehouse"),
			(workstation_subquery.as_("workstation")),
			WorkOrderItem.name.as_("name"),
			WorkOrderItem.idx,
			WorkOrderItem.item_code,
			WorkOrder.planned_start_date.as_("delivery_date"),
			(total_required_qty).as_("total_required_qty"),
			Item.stock_uom,
			WorkOrder.creation,
		)
		.where(
			(WorkOrder.docstatus == 1)
			& (WorkOrder.status == "Not Started")
			& (WorkOrderItem.required_qty > WorkOrderItem.transferred_qty)
		)
		.orderby(WorkOrder.planned_start_date, WorkOrder.creation, WorkOrderItem.idx)
	)

	if name:
		work_order_query = work_order_query.where(WorkOrder.name == name)

	if item_code:
		work_order_query = work_order_query.where(WorkOrderItem.item_code == item_code)

	return work_order_query.run(as_dict=True)


def get_sales_demand(name: str | None = None, item_code: str | None = None) -> list[Demand]:
	SalesOrder = DocType("Sales Order")
	SalesOrderItem = DocType("Sales Order Item")
	Item = DocType("Item")
	BEAMSettings = DocType("BEAM Settings")

	default_fg_warehouse = frappe.db.get_single_value(
		"Manufacturing Settings", "default_fg_warehouse"
	)

	shipping_workstation_subquery = (
		frappe.qb.from_(BEAMSettings)
		.select(BEAMSettings.shipping_workstation)
		.where(BEAMSettings.company == SalesOrder.company)
		.limit(1)
	)

	total_required_qty = Field("stock_qty") - Field("delivered_qty")

	sales_order_query = (
		frappe.qb.from_(SalesOrder)
		.join(SalesOrderItem)
		.on(SalesOrder.name == SalesOrderItem.parent)
		.left_join(Item)
		.on(Item.item_code == SalesOrderItem.item_code)
		.select(
			ConstantColumn("Sales Order").as_("doctype"),
			SalesOrder.name.as_("parent"),
			SalesOrder.company,
			ConstantColumn(default_fg_warehouse).as_("warehouse"),
			(shipping_workstation_subquery.as_("workstation")),
			SalesOrderItem.name.as_("name"),
			SalesOrderItem.idx,
			SalesOrderItem.item_code,
			SalesOrder.delivery_date,
			(total_required_qty).as_("total_required_qty"),
			Item.stock_uom,
			SalesOrder.creation,
		)
		.where(
			(SalesOrder.docstatus == 1)
			& (SalesOrder.status != "Closed")
			& (SalesOrderItem.stock_qty > SalesOrderItem.delivered_qty)
		)
		.orderby(SalesOrder.delivery_date, SalesOrder.creation, SalesOrderItem.idx)
	)

	if name:
		sales_order_query = sales_order_query.where(SalesOrder.name == name)

	if item_code:
		sales_order_query = sales_order_query.where(SalesOrderItem.item_code == item_code)

	return sales_order_query.run(as_dict=True)


def get_receiving_demand(name: str | None = None, item_code: str | None = None) -> list[Demand]:
	PurchaseOrder = DocType("Purchase Order")
	PurchaseOrderItem = DocType("Purchase Order Item")
	Item = DocType("Item")
	BEAMSettings = DocType("BEAM Settings")

	receiving_workstation_subquery = (
		frappe.qb.from_(BEAMSettings)
		.select(BEAMSettings.receiving_workstation)
		.where(BEAMSettings.company == PurchaseOrder.company)
		.limit(1)
	)

	purchase_order_query = (
		frappe.qb.from_(PurchaseOrder)
		.join(PurchaseOrderItem)
		.on(PurchaseOrder.name == PurchaseOrderItem.parent)
		.left_join(Item)
		.on(Item.item_code == PurchaseOrderItem.item_code)
		.select(
			ConstantColumn("Purchase Order").as_("doctype"),
			PurchaseOrder.name.as_("parent"),
			PurchaseOrder.company,
			PurchaseOrderItem.warehouse,
			(receiving_workstation_subquery.as_("workstation")),
			PurchaseOrderItem.name.as_("name"),
			PurchaseOrderItem.idx,
			PurchaseOrderItem.item_code,
			PurchaseOrder.schedule_date,
			PurchaseOrderItem.stock_qty.as_("total_required_qty"),
			Item.stock_uom,
			PurchaseOrder.creation,
		)
		.where((PurchaseOrder.docstatus == 1) & (PurchaseOrder.status != "Closed"))
		.orderby(PurchaseOrder.schedule_date, PurchaseOrder.creation, PurchaseOrderItem.idx)
	)

	if name:
		purchase_order_query = purchase_order_query.where(PurchaseOrder.name == name)

	if item_code:
		purchase_order_query = purchase_order_query.where(PurchaseOrderItem.item_code == item_code)

	return purchase_order_query.run(as_dict=True)


def build_demand_allocation_map() -> None:
	reset_demand_db()
	build_demand_map()
	build_allocation_map()


def get_demand_list(name: str | None = None, item_code: str | None = None) -> list[Demand]:
	if name:
		with get_demand_db() as conn:
			cursor = conn.cursor()

			if item_code:
				demand_query = cursor.execute(
					f"SELECT * FROM demand WHERE parent = '{name}' AND item_code = '{item_code}'"
				)
			else:
				demand_query = cursor.execute(f"SELECT * FROM demand WHERE parent = '{name}'")

			sales_demand: list[Demand] = demand_query.fetchall()
			if sales_demand:
				return sales_demand

	manufacturing_demand = get_manufacturing_demand(name, item_code)
	sales_demand = get_sales_demand(name, item_code)
	return manufacturing_demand + sales_demand


def build_demand_map(
	name: str | None = None, item_code: str | None = None, cursor: Optional["Cursor"] = None
) -> None:
	output: list[Demand] = []

	for row in get_demand_list(name, item_code):
		row.key = row.key or frappe.generate_hash()
		row.delivery_date = str(row.delivery_date or get_epoch_from_datetime(row.delivery_date))
		row.creation = str(row.creation or get_epoch_from_datetime(row.creation))
		row.total_required_qty = str(row.total_required_qty)
		row.idx = str(row.idx)
		output.append(row)

	if output:
		if cursor:
			insert_demand(output, cursor)
		else:
			with get_demand_db() as conn:
				cursor = conn.cursor()
				insert_demand(output, cursor)


def insert_demand(output: list[Demand], cursor: "Cursor") -> None:
	for row in output:
		demand_row = {}
		for key, value in row.items():
			if value:
				demand_row[key] = value
		keys = "', '".join(demand_row.keys())
		values = "', '".join(demand_row.values())
		cursor.execute(f"INSERT INTO demand ('{keys}') VALUES ('{values}')")


def modify_demand(doc: Union["SalesOrder", "WorkOrder"], method: str | None = None) -> None:
	if method == "on_submit":
		add_demand_allocation(doc.name)
	elif method == "on_cancel":
		remove_demand_allocation(doc.name)


def get_allocation_list(name: str) -> list[Allocation]:
	with get_demand_db() as conn:
		cursor = conn.cursor()
		query = f"SELECT * FROM allocation WHERE parent = '{name}'"
		return cursor.execute(query).fetchall()


def add_demand_allocation(name: str) -> None:
	build_demand_map(name)
	build_allocation_map()


def remove_demand_allocation(name: str) -> None:
	with get_demand_db() as conn:
		cursor = conn.cursor()
		# remove all allocated row(s)
		allocations = get_allocation_list(name)
		for allocation in allocations:
			cursor.execute(f"DELETE FROM allocation WHERE key = '{allocation.key}'")

		# remove all demand row(s)
		demand = get_demand_list(name)
		for row in demand:
			cursor.execute(f"DELETE FROM demand WHERE key = '{row.key}'")


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
	row: Union[
		"DeliveryNoteItem",
		"PurchaseInvoiceItem",
		"PurchaseReceiptItem",
		"SalesInvoiceItem",
		"StockEntryDetail",
		"StockReconciliationItem",
		None,
	] = None,
):
	item_filter = f"WHERE item_code = '{row.item_code}'" if row else ""

	with get_demand_db() as conn:
		cursor = conn.cursor()
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
			{item_filter}
			ORDER BY
				delivery_date ASC;
			"""
		)


def get_item_demand_map(
	row: Union[
		"DeliveryNoteItem",
		"PurchaseInvoiceItem",
		"PurchaseReceiptItem",
		"SalesInvoiceItem",
		"StockEntryDetail",
		"StockReconciliationItem",
		None,
	] = None,
) -> dict[str, list[Allocation | Demand]]:
	demand_query = get_demand_query(row=row)
	demand_rows: list[Allocation | Demand] = demand_query.fetchall()

	item_demand_map = frappe._dict()
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
		cursor = conn.cursor()

		quantity_field = action.get("quantity_field")
		row_qty = row.get(quantity_field) if quantity_field else None

		warehouse_field = action.get("warehouse_field")
		warehouse = row.get(warehouse_field)

		allocation_query = cursor.execute(
			f"""
			SELECT *
			FROM allocation
			WHERE item_code = '{row.item_code}' AND warehouse = '{warehouse}' AND allocated_qty > 0
			"""
		)

		# TODO: remove demand row if demand is fully satisfied

		existing_allocations: list[Allocation] = allocation_query.fetchall()
		if existing_allocations:
			allocation_effect = action.get("allocation_effect")
			demand_effect = action.get("demand_effect")

			for allocation in existing_allocations:
				demand_query = cursor.execute(f"SELECT * FROM demand WHERE key = '{allocation.demand}'")
				demand_row: Demand = demand_query.fetchone()

				if demand_row:
					# demand is still pending, add/reverse allocation;
					# process demand before allocation

					new_total_required_qty = demand_row.total_required_qty
					if demand_effect:
						if demand_effect == "increase":
							new_total_required_qty = demand_row.total_required_qty + row_qty
						elif demand_effect == "decrease":
							new_total_required_qty = max(0, demand_row.total_required_qty - row_qty)

						if new_total_required_qty <= 0:
							# if demand is fully met, delete the demand row
							cursor.execute(f"DELETE FROM demand WHERE key = '{demand_row.key}'")
						else:
							# if demand is partially met, update demand row
							cursor.execute(
								f"UPDATE demand SET total_required_qty = {new_total_required_qty} WHERE key = '{demand_row.key}'"
							)

					if allocation_effect == "increase":
						new_allocated_qty = min(new_total_required_qty, allocation.allocated_qty + row_qty)
					elif allocation_effect == "decrease":
						new_allocated_qty = max(0, allocation.allocated_qty - row_qty)
					elif allocation_effect == "adjustment":
						new_allocated_qty = min(new_total_required_qty, row_qty)

					if new_allocated_qty <= 0:
						# if partial allocation is reverted, delete the allocation row
						cursor.execute(f"DELETE FROM allocation WHERE key = '{allocation.key}'")
					else:
						# if demand can be partially or fully met, update allocation row
						cursor.execute(
							f"UPDATE allocation SET allocated_qty = {new_allocated_qty} WHERE key = '{allocation.key}'"
						)
				else:
					# demand is already satisfied, reverse allocation

					if allocation_effect == "increase":
						new_allocated_qty = allocation.allocated_qty + row_qty
						cursor.execute(
							f"UPDATE allocation SET allocated_qty = {new_allocated_qty} WHERE key = '{allocation.key}'"
						)
					elif allocation_effect in ["increase", "adjustment"]:
						# TODO: are these cases possible?
						pass

					if demand_effect == "increase":
						build_demand_map(row.parent, row.item_code, cursor)
					elif demand_effect == "decrease":
						# TODO: is this case possible?
						pass
		else:
			item_demand_map = get_item_demand_map(row=row)
			demand_rows = item_demand_map.get(row.item_code)
			if not demand_rows:
				return
			demand_queue = deque(demand_rows)

			allocations: list[Allocation] = []
			while demand_queue:
				current_demand = demand_queue[0]
				net_required_qty = current_demand["net_required_qty"]

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
				cursor.execute(
					f"""INSERT INTO allocation ('{"', '".join(allocation.keys())}') VALUES ('{"', '".join(allocation.values())}')"""
				)


def create_allocations():
	with get_demand_db() as conn:
		cursor = conn.cursor()

		item_demand_map = get_item_demand_map()

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
			cursor.execute(
				f"""INSERT INTO allocation ('{"', '".join(allocation.keys())}') VALUES ('{"', '".join(allocation.values())}')"""
			)


def new_allocation(demand_row: Demand):
	return frappe._dict(
		{
			"key": frappe.generate_hash(),
			"demand": demand_row.key,
			"doctype": demand_row.doctype,
			"company": demand_row.company,
			"parent": demand_row.parent,
			"name": demand_row.name,
			"idx": str(demand_row.idx),
			"item_code": demand_row.item_code,
			"allocated_date": str(get_epoch_from_datetime()),
			"modified": str(get_epoch_from_datetime()),
			"stock_uom": demand_row.stock_uom,
			"status": "Soft Allocated",
			"assigned": demand_row.assigned or "",
			"creation": str(demand_row.creation),
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

	demand_warehouses = get_demand_warehouses(doc.get("company"))
	for row in doc.get("items"):
		for action in method_matrix:
			# implicit conditions: skip allocation for non-demand warehouses
			warehouse_field = action.get("warehouse_field")
			if warehouse_field:
				warehouse = row.get(warehouse_field)
				if warehouse not in demand_warehouses:
					continue

			# explicit conditions
			conditions = action.get("conditions")
			if conditions:
				for key, value in conditions.items():
					if doc.get(key) == value:
						build_allocation_map(row=row, action=action)
			else:
				build_allocation_map(row=row, action=action)


def get_demand_warehouses(company: str | None = None) -> list[str]:
	if not company:
		company = frappe.defaults.get_defaults().get("company")

	root_warehouse = frappe.get_all(
		"Warehouse",
		{"company": company, "is_group": True, "parent_warehouse": ["is", "not set"]},
		pluck="name",
	)[0]

	return get_descendant_warehouses(company, root_warehouse)


def get_descendant_warehouses(company: str, warehouse: str) -> list[str]:
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
def get_demand(*args, **kwargs) -> list[Demand]:
	records_per_page = 20
	page = kwargs.get("page", 1)
	order_by = kwargs.get("order_by", "workstation, assigned")

	a_filters = d_filters = ""
	if kwargs.get("filters"):
		filters = kwargs.get("filters")
		if filters:
			d_filters = "AND " + "\nAND ".join(
				[f"d.{key} IN ('{value}')" for key, value in filters.items()]
			)
			a_filters = "AND " + "\nAND ".join(
				[f"a.{key} IN ('{value}')" for key, value in filters.items()]
			)

		# if assigned:
		# 	_filters += f" AND assigned LIKE %{assigned}%"

	demand_query = f"""
		SELECT
			d.key,
			'' AS demand,
			d.doctype,
			d.company,
			d.parent,

			d.warehouse,
			d.name,
			d.idx,
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
			d.assigned,
			d.creation
		FROM demand d
		WHERE allocated_qty <= 0
		{d_filters}
	"""

	allocation_query = f"""
		SELECT
			a.key,
			a.demand,
			a.doctype,
			a.company,
			a.parent,

			a.warehouse,
			a.name,
			a.idx,
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
			a.assigned,
			a.creation
		FROM allocation a
		WHERE allocated_qty > 0
		{a_filters}
		ORDER BY delivery_date, idx, creation, parent ASC
	"""

	record_offset = records_per_page * (page - 1)
	query = (
		f"{demand_query} UNION ALL {allocation_query} LIMIT {records_per_page} OFFSET {record_offset}"
	)

	with get_demand_db() as conn:
		cursor = conn.cursor()
		rows: list[Allocation | Demand] = cursor.execute(query).fetchall()
		for row in rows:
			row.update(
				{
					"net_required_qty": max(0.0, row.net_required_qty),
					"delivery_date": get_datetime_from_epoch(row.delivery_date),
					"allocated_date": get_datetime_from_epoch(row.allocated_date),
					"modified": get_datetime_from_epoch(row.modified),
					"creation": get_datetime_from_epoch(row.creation),
				}
			)
		return rows
