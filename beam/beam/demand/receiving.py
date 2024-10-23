# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

from typing import TYPE_CHECKING, Optional, Union

import frappe
from frappe.query_builder import DocType
from frappe.query_builder.custom import ConstantColumn
from frappe.query_builder.functions import Coalesce
from pypika import Query, Table
from pypika.terms import ValueWrapper

from beam.beam.demand.sqlite import get_demand_db, reset_receiving_db
from beam.beam.demand.utils import Receiving, get_datetime_from_epoch, get_epoch_from_datetime

if TYPE_CHECKING:
	from sqlite3 import Cursor

	from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import PurchaseInvoice
	from erpnext.buying.doctype.purchase_invoice.purchase_invoice import PurchaseOrder


def _get_receiving_demand(
	name: str | None = None, item_code: str | None = None
) -> list[Receiving]:
	PurchaseOrder = DocType("Purchase Order")
	PurchaseOrderItem = DocType("Purchase Order Item")
	Item = DocType("Item")
	BEAMSettings = DocType("BEAM Settings")

	# Purchase Order
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
			PurchaseOrderItem.stock_qty.as_("stock_qty"),
			Item.stock_uom,
			PurchaseOrder.creation,
		)
		.where(
			(PurchaseOrder.docstatus == 1)
			& (PurchaseOrder.status != "Closed")
			& (Item.is_stock_item == 1)
			& (PurchaseOrderItem.delivered_by_supplier != 1)
		)
		.orderby(PurchaseOrder.schedule_date, PurchaseOrder.creation, PurchaseOrderItem.idx)
	)

	if name:
		purchase_order_query = purchase_order_query.where(PurchaseOrder.name == name)

	if item_code:
		purchase_order_query = purchase_order_query.where(PurchaseOrderItem.item_code == item_code)

	purchase_orders = purchase_order_query.run(as_dict=True)

	# Purchase Invoice
	PurchaseInvoice = frappe.qb.DocType("Purchase Invoice")
	PurchaseInvoiceItem = frappe.qb.DocType("Purchase Invoice Item")

	receiving_workstation_subquery = (
		frappe.qb.from_(BEAMSettings)
		.select(BEAMSettings.receiving_workstation)
		.where(BEAMSettings.company == PurchaseInvoice.company)
		.limit(1)
	)

	unreceived_purchase_invoices_query = (
		frappe.qb.from_(PurchaseInvoice)
		.join(PurchaseInvoiceItem)
		.on(PurchaseInvoice.name == PurchaseInvoiceItem.parent)
		.left_join(Item)
		.on(Item.item_code == PurchaseInvoiceItem.item_code)
		.select(
			ConstantColumn("Purchase Invoice").as_("doctype"),
			PurchaseInvoice.name.as_("parent"),
			PurchaseInvoice.company,
			PurchaseInvoiceItem.warehouse,
			(receiving_workstation_subquery.as_("workstation")),
			PurchaseInvoiceItem.name.as_("name"),
			PurchaseInvoiceItem.idx,
			PurchaseInvoiceItem.item_code,
			PurchaseInvoice.due_date.as_("schedule_date"),
			PurchaseInvoiceItem.stock_qty.as_("stock_qty"),
			Item.stock_uom,
			PurchaseInvoice.creation,
		)
		.where(
			(PurchaseInvoice.docstatus == 1)
			& (Coalesce(PurchaseInvoiceItem.purchase_order, "") == "")
			& (PurchaseInvoiceItem.received_qty < PurchaseInvoiceItem.stock_qty)
			& (Item.is_stock_item == 1)
		)
		.orderby(PurchaseInvoice.due_date, PurchaseInvoice.creation, PurchaseInvoiceItem.idx)
	)

	if name:
		unreceived_purchase_invoices_query = unreceived_purchase_invoices_query.where(
			PurchaseInvoice.name == name
		)

	if item_code:
		unreceived_purchase_invoices_query = unreceived_purchase_invoices_query.where(
			PurchaseInvoiceItem.item_code == item_code
		)

	unreceived_purchase_invoices = unreceived_purchase_invoices_query.run(as_dict=True)

	# Subcontracting Order
	return purchase_orders + unreceived_purchase_invoices


def modify_receiving(
	doc: Union["PurchaseOrder", "PurchaseInvoice"], method: str | None = None
) -> None:
	if method == "on_submit":
		add_receiving(doc.name)
	elif method == "on_cancel":
		remove_receiving(doc.name)


def add_receiving(name: str) -> None:
	build_receiving_map(name)


def remove_receiving(name: str) -> None:
	with get_demand_db() as conn:
		cursor = conn.cursor()
		# remove all receiving row(s)
		receiving = get_receiving_list(name)
		receiving_table = Table("receiving")
		for row in receiving:
			delete_query = Query.from_(receiving_table).delete().where(receiving_table.key == row.key)
			cursor.execute(delete_query.get_sql())


def get_receiving_list(name: str | None = None, item_code: str | None = None) -> list[Receiving]:
	if name:
		with get_demand_db() as conn:
			cursor = conn.cursor()
			receiving_table = Table("receiving")

			if item_code:
				receiving_query = (
					Query.from_(receiving_table)
					.select("*")
					.where((receiving_table.parent == name) & (receiving_table.item_code == item_code))
				)
			else:
				receiving_query = (
					Query.from_(receiving_table).select("*").where(receiving_table.parent == name)
				)

			receiving_query = cursor.execute(receiving_query.get_sql())

			receiving_demand: list[Receiving] = receiving_query.fetchall()
			if receiving_demand:
				return receiving_demand

	return _get_receiving_demand(name, item_code)


def reset_build_receiving_map() -> None:
	reset_receiving_db()
	build_receiving_map()


def build_receiving_map(
	name: str | None = None, item_code: str | None = None, cursor: Optional["Cursor"] = None
) -> None:
	output: list[Receiving] = []

	for row in get_receiving_list(name, item_code):
		row.key = row.key or frappe.generate_hash()
		row.schedule_date = str(row.schedule_date or get_epoch_from_datetime(row.schedule_date))
		row.creation = str(row.creation or get_epoch_from_datetime(row.creation))
		row.stock_qty = str(row.stock_qty)
		row.idx = str(row.idx)
		output.append(row)

	if output:
		if cursor:
			insert_receiving(output, cursor)
		else:
			with get_demand_db() as conn:
				cursor = conn.cursor()
				insert_receiving(output, cursor)


def insert_receiving(output: list[Receiving], cursor: "Cursor") -> None:
	receiving_table = Table("receiving")
	for row in output:
		receiving_row = {key: value for key, value in row.items() if value}
		insert_query = (
			Query.into(receiving_table).columns(*receiving_row.keys()).insert(*receiving_row.values())
		)
		cursor.execute(insert_query.get_sql())


def get_receiving_demand(*args, **kwargs) -> list[Receiving]:
	records_per_page = 20
	page = int(kwargs.get("page", 1))
	order_by = kwargs.get("order_by", "workstation, assigned")

	receiving = Table("receiving")

	r_filters = []

	if kwargs.get("filters"):
		filters = kwargs["filters"]
		for key, value in filters.items():
			if isinstance(value, str):
				value = (value,)
			r_filters.append(getattr(receiving, key).isin(value))

	receiving_query = Query.from_(receiving).select(
		receiving.key,
		receiving.doctype,
		receiving.company,
		receiving.parent,
		receiving.warehouse,
		receiving.name,
		receiving.idx,
		receiving.item_code,
		receiving.schedule_date,
		receiving.modified,
		receiving.stock_uom,
		receiving.stock_qty,
		ValueWrapper("").as_("status"),
		receiving.assigned,
		receiving.creation,
	)

	if r_filters:
		receiving_query = receiving_query.where(*r_filters)

	record_offset = records_per_page * (page - 1)

	query = f"{receiving_query} LIMIT {records_per_page} OFFSET {record_offset}"

	with get_demand_db() as conn:
		cursor = conn.cursor()
		rows: list[Receiving] = cursor.execute(query).fetchall()
		for row in rows:
			row.update(
				{
					"stock_qty": max(0.0, row.stock_qty),
					"schedule_date": get_datetime_from_epoch(row.schedule_date),
					"modified": get_datetime_from_epoch(row.modified),
					"creation": get_datetime_from_epoch(row.creation),
				}
			)
		return rows
