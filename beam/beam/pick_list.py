# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import flt

TRANSFER_PURPOSES = ("Material Transfer for Manufacture", "Material Transfer")


def fill_handling_units_on_stock_entry(stock_entry):
	settings = frappe.get_cached_doc("BEAM Settings", stock_entry.company)
	if not settings.enable_handling_units:
		return

	for row in stock_entry.items:
		if not frappe.get_value("Item", row.item_code, "enable_handling_unit"):
			continue
		if row.handling_unit:
			continue
		hu_rows = frappe.get_all(
			"Stock Ledger Entry",
			filters={
				"item_code": row.item_code,
				"warehouse": row.s_warehouse,
				"handling_unit": ["is", "set"],
				"is_cancelled": 0,
			},
			pluck="handling_unit",
			order_by="posting_datetime desc, creation desc",
			limit=1,
		)
		if hu_rows:
			row.handling_unit = hu_rows[0]


def create_stock_entry_on_submit(doc, method=None):
	if doc.docstatus != 1:
		return
	if doc.purpose not in TRANSFER_PURPOSES:
		return

	settings = frappe.get_cached_doc("BEAM Settings", doc.company)
	if not settings.get("create_stock_entry_on_pick_list_submit"):
		return

	from erpnext.stock.doctype.pick_list.pick_list import create_stock_entry

	stock_entry_dict = create_stock_entry(doc.as_dict())
	if not stock_entry_dict or not isinstance(stock_entry_dict, dict):
		return
	if not stock_entry_dict.get("items"):
		return

	stock_entry = frappe.get_doc(stock_entry_dict)
	apply_shipping_target_warehouse(stock_entry, settings, doc.purpose)
	fill_handling_units_on_stock_entry(stock_entry)
	stock_entry.insert()
	stock_entry.submit()


def apply_shipping_target_warehouse(stock_entry, settings, purpose):
	if purpose != "Material Transfer":
		return
	target = settings.get("shipping_warehouse")
	if not target:
		return
	stock_entry.to_warehouse = target
	for row in stock_entry.items:
		if not row.t_warehouse:
			row.t_warehouse = target


def get_open_pick_list_for_work_order(work_order_id: str) -> str | None:
	"""Return the name of an open Pick List linked to this work order, if any."""
	pick_list = frappe.qb.DocType("Pick List")
	row = (
		frappe.qb.from_(pick_list)
		.select(pick_list.name)
		.where(
			(pick_list.work_order == work_order_id)
			& (pick_list.docstatus.isin([0, 1]))
			& (pick_list.status.notin(["Completed", "Cancelled"]))
		)
		.orderby(pick_list.modified, order=frappe.qb.desc)
		.limit(1)
	).run(as_dict=True)
	if row:
		return row[0].name
	return None


def pick_list_fully_picked(doc) -> bool:
	for location in doc.locations:
		if flt(location.picked_qty) < flt(location.stock_qty):
			return False
	return bool(doc.locations)


def sorted_open_locations(doc):
	rows = [row for row in doc.locations if flt(row.picked_qty) < flt(row.stock_qty)]
	return sorted(rows, key=lambda row: (row.warehouse or "", row.item_code or ""))


@frappe.whitelist()
def apply_pick_list_scan(
	pick_list_name: str,
	barcode: str,
	warehouse_gate: str | None = None,
	picked_quantities: str | dict | None = None,
):
	"""Validate one scan against the next open line.

	picked_quantities maps location idx to the client's unsaved picked_qty, so lines
	picked since the last SAVE count as done.
	"""
	from beam.beam.scan import get_barcode_context, get_handling_unit

	frappe.has_permission("Pick List", "write", throw=True)
	doc = frappe.get_doc("Pick List", pick_list_name)
	if doc.docstatus != 0:
		frappe.throw(frappe._("This pick list can no longer be edited."), frappe.ValidationError)

	if picked_quantities:
		parsed = (
			frappe.parse_json(picked_quantities)
			if isinstance(picked_quantities, str)
			else picked_quantities
		)
		if isinstance(parsed, dict):
			for location in doc.locations:
				client_qty = parsed.get(str(location.idx))
				if client_qty is not None:
					location.picked_qty = flt(client_qty)

	open_rows = sorted_open_locations(doc)
	if not open_rows:
		return {"ok": False, "message": frappe._("All lines are fully picked.")}

	current = open_rows[0]
	barcode_doc = get_barcode_context(barcode)
	if not barcode_doc:
		return {"ok": False, "message": frappe._("Barcode not found.")}

	scanned_doctype = barcode_doc.doc.doctype
	if scanned_doctype == "Warehouse":
		if barcode_doc.doc.name == current.warehouse:
			return {"ok": True, "warehouse_gate": current.warehouse, "item_code": current.item_code}
		return {"ok": False, "message": frappe._("Wrong warehouse for the next pick line.")}

	if warehouse_gate != current.warehouse:
		return {"ok": False, "message": frappe._("Scan the warehouse bin before picking stock.")}

	item_code = None
	increment = flt(1)
	if scanned_doctype == "Handling Unit":
		hu = get_handling_unit(barcode_doc.doc.name, "Pick List")
		if hu.warehouse != current.warehouse:
			return {"ok": False, "message": frappe._("Handling unit is not in this warehouse.")}
		item_code = hu.item_code
		increment = flt(hu.stock_qty)
	elif scanned_doctype == "Item":
		item_code = barcode_doc.doc.name
	else:
		return {"ok": False, "message": frappe._("Scan a warehouse, item, or handling unit.")}

	if item_code != current.item_code:
		return {"ok": False, "message": frappe._("Wrong item for the next pick line.")}

	remaining = flt(current.stock_qty) - flt(current.picked_qty)
	new_picked_qty = flt(current.picked_qty) + min(increment, remaining)

	return {
		"ok": True,
		"warehouse_gate": None,
		"item_code": current.item_code,
		"idx": current.idx,
		"picked_qty": new_picked_qty,
		"stock_qty": current.stock_qty,
	}
