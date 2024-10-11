# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

from collections import deque
from typing import TYPE_CHECKING, Any, Optional, Union

import frappe
from frappe.utils.data import flt
from frappe.utils.nestedset import get_descendants_of
from pypika import Query, Table
from pypika import functions as fn
from pypika.terms import Order, ValueWrapper

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
	manufacturing_demand = []

	if name:
		filters = {"docstatus": 1, "status": "Not Started", "name": name}
	else:
		filters = {"docstatus": 1, "status": "Not Started"}

	pending_work_orders = frappe.get_all(
		"Work Order",
		filters=filters,
		fields=["name", "company", "wip_warehouse", "planned_start_date", "creation"],
		order_by="planned_start_date ASC, creation ASC",
	)

	for work_order in pending_work_orders:
		if item_code:
			filters = {"parent": work_order.name, "item_code": item_code}
		else:
			filters = {"parent": work_order.name}

		work_order_items = frappe.get_all(
			"Work Order Item",
			filters=filters,
			fields=["name", "item_code", "required_qty", "transferred_qty", "idx"],
			order_by="idx ASC",
		)
		workstation = frappe.get_all(
			"Work Order Operation",
			filters={"parent": work_order.name},
			fields=["workstation"],
			order_by="idx ASC",
		)
		workstation = workstation[0].get("workstation") if workstation else None

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
						"workstation": workstation or "",
						"name": item.name,
						"idx": item.idx,
						"item_code": item.item_code,
						"delivery_date": work_order.planned_start_date,
						"total_required_qty": item.required_qty - item.transferred_qty,
						"stock_uom": frappe.db.get_value("Item", item.item_code, "stock_uom"),
						"creation": work_order.creation,
					}
				)
			)

	return manufacturing_demand


def get_sales_demand(name: str | None = None, item_code: str | None = None) -> list[Demand]:
	sales_demand = []
	default_fg_warehouse = frappe.db.get_single_value(
		"Manufacturing Settings", "default_fg_warehouse"
	)

	if name:
		filters = {"docstatus": 1, "status": ["!=", "Closed"], "name": name}
	else:
		filters = {"docstatus": 1, "status": ["!=", "Closed"]}

	sales_orders = frappe.get_all(
		"Sales Order",
		filters=filters,
		fields=["name", "company", "delivery_date", "creation"],
		order_by="delivery_date ASC, creation ASC, name ASC",
	)

	shipping_workstations = {
		s.company: s.shipping_workstation
		for s in frappe.get_all("BEAM Settings", ["company", "shipping_workstation"])
	}

	for sales_order in sales_orders:
		if item_code:
			filters = {"parent": sales_order.name, "item_code": item_code}
		else:
			filters = {"parent": sales_order.name}

		sales_order_items = frappe.get_all(
			"Sales Order Item",
			filters=filters,
			fields=["name", "item_code", "stock_qty", "delivered_qty", "idx"],
			order_by="delivery_date, idx ASC",
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
						"workstation": shipping_workstations.get(sales_order.company) or "",
						"name": item.name,
						"idx": item.idx,
						"item_code": item.item_code,
						"delivery_date": sales_order.delivery_date,
						"total_required_qty": item.stock_qty - item.delivered_qty,
						"stock_uom": frappe.db.get_value("Item", item.item_code, "stock_uom"),
						"creation": sales_order.creation,
					}
				)
			)

	return sales_demand


def build_demand_allocation_map() -> None:
	reset_demand_db()
	build_demand_map()
	build_allocation_map()


def get_demand_list(name: str | None = None, item_code: str | None = None) -> list[Demand]:
	if name:
		with get_demand_db() as conn:
			cursor = conn.cursor()
			demand_table = Table("demand")

			if item_code:
				demand_query = (
					Query.from_(demand_table)
					.select("*")
					.where((demand_table.parent == name) & (demand_table.item_code == item_code))
				)
			else:
				demand_query = Query.from_(demand_table).select("*").where(demand_table.parent == name)

			demand_query = cursor.execute(demand_query.get_sql())

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
	demand_table = Table("demand")
	for row in output:
		demand_row = {key: value for key, value in row.items() if value}
		insert_query = Query.into(demand_table).columns(*demand_row.keys()).insert(*demand_row.values())
		cursor.execute(insert_query.get_sql())


def modify_demand(doc: Union["SalesOrder", "WorkOrder"], method: str | None = None) -> None:
	if method == "on_submit":
		add_demand_allocation(doc.name)
	elif method == "on_cancel":
		remove_demand_allocation(doc.name)


def get_allocation_list(name: str) -> list[Allocation]:
	with get_demand_db() as conn:
		allocation_table = Table("allocation")
		cursor = conn.cursor()
		query = Query.from_(allocation_table).select("*").where(allocation_table.parent == name)
		return cursor.execute(query.get_sql()).fetchall()


def add_demand_allocation(name: str) -> None:
	build_demand_map(name)
	build_allocation_map()


def remove_demand_allocation(name: str) -> None:
	with get_demand_db() as conn:
		allocation_table = Table("allocation")
		demand_table = Table("demand")
		cursor = conn.cursor()

		# remove all allocated row(s)
		allocations = get_allocation_list(name)
		for allocation in allocations:
			delete_query = (
				Query.from_(allocation_table).delete().where(allocation_table.key == allocation.key)
			)
			cursor.execute(delete_query.get_sql())

		# remove all demand row(s)
		demand = get_demand_list(name)
		for row in demand:
			delete_query = Query.from_(demand_table).delete().where(demand_table.key == row.key)
			cursor.execute(delete_query.get_sql())


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
	demand_table = Table("demand")
	allocation_table = Table("allocation")

	query = (
		Query.from_(demand_table)
		.select(
			demand_table.star,
			fn.Coalesce(fn.Sum(allocation_table.allocated_qty), 0).as_("allocated_qty"),
			(demand_table.total_required_qty - fn.Coalesce(fn.Sum(allocation_table.allocated_qty), 0)).as_(
				"net_required_qty"
			),
		)
		.left_join(allocation_table)
		.on(allocation_table.demand == demand_table.key)
	)

	if row:
		query = query.where(demand_table.item_code == row.item_code)

	query = query.groupby(
		demand_table.key,
		demand_table.item_code,
		demand_table.total_required_qty,
		demand_table.delivery_date,
	).orderby(demand_table.delivery_date)

	with get_demand_db() as conn:
		cursor = conn.cursor()
		return cursor.execute(query.get_sql())


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
	demand_table = Table("demand")
	allocation_table = Table("allocation")

	with get_demand_db() as conn:
		cursor = conn.cursor()

		quantity_field = action.get("quantity_field")
		row_qty = row.get(quantity_field) if quantity_field else None

		warehouse_field = action.get("warehouse_field")
		warehouse = row.get(warehouse_field)

		allocation_query = (
			Query.from_(allocation_table)
			.select("*")
			.where(
				(allocation_table.item_code == row.item_code)
				& (allocation_table.warehouse == warehouse)
				& (allocation_table.allocated_qty > 0)
			)
		)
		allocation_query = cursor.execute(allocation_query.get_sql())

		# TODO: remove demand row if demand is fully satisfied

		existing_allocations: list[Allocation] = allocation_query.fetchall()
		if existing_allocations:
			allocation_effect = action.get("allocation_effect")
			demand_effect = action.get("demand_effect")

			for allocation in existing_allocations:
				demand_query = (
					Query.from_(demand_table).select("*").where(demand_table.key == allocation.demand)
				)
				demand_query = cursor.execute(demand_query.get_sql())
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
							delete_query = Query.from_(demand_table).delete().where(demand_table.key == demand_row.key)
							cursor.execute(delete_query.get_sql())
						else:
							# if demand is partially met, update demand row
							update_query = (
								Query.update(demand_table)
								.set(demand_table.total_required_qty, new_total_required_qty)
								.where(demand_table.key == demand_row.key)
							)
							cursor.execute(update_query.get_sql())

					if allocation_effect == "increase":
						new_allocated_qty = min(new_total_required_qty, allocation.allocated_qty + row_qty)
					elif allocation_effect == "decrease":
						new_allocated_qty = max(0, allocation.allocated_qty - row_qty)
					elif allocation_effect == "adjustment":
						new_allocated_qty = min(new_total_required_qty, row_qty)

					if new_allocated_qty <= 0:
						# if partial allocation is reverted, delete the allocation row
						delete_query = (
							Query.from_(allocation_table).delete().where(allocation_table.key == allocation.key)
						)
						cursor.execute(delete_query.get_sql())
					else:
						# if demand can be partially or fully met, update allocation row
						update_query = (
							Query.update(allocation_table)
							.set(allocation_table.allocated_qty, new_allocated_qty)
							.where(allocation_table.key == allocation.key)
						)
						cursor.execute(update_query.get_sql())
				else:
					# demand is already satisfied, reverse allocation

					if allocation_effect == "increase":
						new_allocated_qty = allocation.allocated_qty + row_qty
						update_query = (
							Query.update(allocation_table)
							.set(allocation_table.allocated_qty, new_allocated_qty)
							.where(allocation_table.key == allocation.key)
						)
						cursor.execute(update_query.get_sql())
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
				insert_query = (
					Query.into(allocation_table).columns(*allocation.keys()).insert(*allocation.values())
				)
				cursor.execute(insert_query.get_sql())


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
			allocation_table = Table("allocation")
			insert_query = (
				Query.into(allocation_table).columns(*allocation.keys()).insert(*allocation.values())
			)
			cursor.execute(insert_query.get_sql())


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


def get_demand(*args, **kwargs) -> list[Demand]:
	records_per_page = 20
	page = int(kwargs.get("page", 1))
	order_by = kwargs.get("order_by", "workstation, assigned")

	demand = Table("demand")
	allocation = Table("allocation")

	d_filters = a_filters = []
	if kwargs.get("filters"):
		filters = kwargs.get("filters")
		if filters:
			for key, value in filters.items():
				d_filters.append(demand[key].is_in(value))
				a_filters.append(allocation[key].is_in(value))

	demand_query = (
		Query.from_(demand)
		.select(
			demand.key,
			ValueWrapper("").as_("demand"),
			demand.doctype,
			demand.company,
			demand.parent,
			demand.warehouse,
			demand.name,
			demand.idx,
			demand.item_code,
			demand.delivery_date.as_("allocated_date"),
			demand.delivery_date,
			demand.modified,
			demand.stock_uom,
			fn.Coalesce(
				(
					Query.from_(allocation)
					.select(fn.Sum(allocation.allocated_qty))
					.where(allocation.demand == demand.key)
				),
				0,
			).as_("allocated_qty"),
			(
				demand.total_required_qty
				- fn.Coalesce(
					(
						Query.from_(allocation)
						.select(fn.Sum(allocation.allocated_qty))
						.where(allocation.demand == demand.key)
					),
					0,
				)
			).as_("net_required_qty"),
			demand.total_required_qty,
			ValueWrapper("").as_("status"),
			demand.assigned,
			demand.creation,
		)
		.where(
			fn.Coalesce(
				(
					Query.from_(allocation)
					.select(fn.Sum(allocation.allocated_qty))
					.where(allocation.demand == demand.key)
				),
				0,
			)
			<= 0
		)
	)

	if d_filters:
		demand_query = demand_query.where(*d_filters)

	allocation_query = (
		Query.from_(allocation)
		.select(
			allocation.key,
			allocation.demand,
			allocation.doctype,
			allocation.company,
			allocation.parent,
			allocation.warehouse,
			allocation.name,
			allocation.idx,
			allocation.item_code,
			allocation.allocated_date,
			allocation.allocated_date.as_("delivery_date"),
			allocation.modified,
			allocation.stock_uom,
			allocation.allocated_qty,
			(
				fn.Coalesce(
					(
						Query.from_(demand).select(demand.total_required_qty).where(allocation.demand == demand.key)
					),
					0,
				)
				- fn.Coalesce(
					fn.Sum(
						Query.from_(allocation)
						.select(allocation.allocated_qty)
						.where(allocation.demand == allocation.demand)
					),
					0,
				)
			).as_("net_required_qty"),
			(
				Query.from_(demand).select(demand.total_required_qty).where(allocation.demand == demand.key)
			).as_("total_required_qty"),
			allocation.status,
			allocation.assigned,
			allocation.creation,
		)
		.where(allocation.allocated_qty > 0)
		.orderby(
			allocation.delivery_date,
			allocation.idx,
			allocation.creation,
			allocation.parent,
			order=Order.asc,
		)
	)

	if a_filters:
		allocation_query = allocation_query.where(*a_filters)

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
