import datetime
import json
from typing import Any, Optional, Union

import frappe


@frappe.whitelist()
def scan(
	barcode: str,
	context: Optional[Union[str, dict[str, Any]]] = None,
	current_qty: Optional[Union[str, float]] = None,
) -> Union[list[dict[str, Any]], None]:
	context = frappe._dict(json.loads(context) if isinstance(context, str) else context)
	barcode_doc = get_barcode_context(barcode)
	if not barcode_doc:
		frappe.msgprint("Barcode not found", alert=True)
		return
	if "listview" in context:
		return get_list_action(barcode_doc, context)
	elif "frm" in context:
		return get_form_action(barcode_doc, context)  # TODO: add current_qty argument here


def get_barcode_context(barcode: str) -> Union[frappe._dict, None]:
	item_barcode = frappe.db.get_value(
		"Item Barcode", {"barcode": barcode}, ["parent", "parenttype"], as_dict=True
	)
	if not item_barcode:
		return
	return frappe._dict(
		{
			"doc": frappe.get_doc(item_barcode.parenttype, item_barcode.parent),
			"barcode": barcode,
		}
	)


def get_handling_unit(handling_unit: str) -> frappe._dict:
	sl_entries = frappe.get_all(
		"Stock Ledger Entry",
		filters={"handling_unit": handling_unit},
		fields=[
			"item_code",
			"SUM(actual_qty) as actual_qty",
			"handling_unit",
			"voucher_type",
			"voucher_no",
			"voucher_detail_no",
			"posting_date",
			"posting_time",
			"valuation_rate",
			"warehouse",
		],
		group_by="handling_unit",
		order_by="modified DESC",
		limit=1,
	)

	for sle in sl_entries:
		if sle.voucher_type == "Stock Entry":
			(
				sle.uom,
				sle.qty,
				sle.conversion_factor,
				sle.stock_uom,
				sle.row_no,
				sle.item_name,
			) = frappe.db.get_value(
				"Stock Entry Detail",
				sle.voucher_detail_no,
				["uom", "qty", "conversion_factor", "stock_uom", "idx", "item_name"],
			)
			sle.stock_qty = sle.actual_qty
			sle.qty = sle.actual_qty / sle.conversion_factor
		else:
			(
				sle.uom,
				sle.qty,
				sle.conversion_factor,
				sle.stock_uom,
				sle.row_no,
				sle.item_name,
			) = frappe.db.get_value(
				f"{sle.voucher_type} Item",
				sle.voucher_detail_no,
				["uom", "qty", "conversion_factor", "stock_uom", "idx", "item_name"],
			)
			sle.stock_qty = sle.actual_qty
			sle.qty = sle.actual_qty / sle.conversion_factor

		sle.conversion_factor = frappe.get_value(
			"UOM Conversion Detail",
			{"parent": sle.item_code, "uom": sle.uom},
			"conversion_factor",
		)
		sle.posting_datetime = (
			datetime.datetime(sle.posting_date.year, sle.posting_date.month, sle.posting_date.day)
			+ sle.posting_time
		)
		sle.user = frappe.session.user
		sle.pop("posting_date")
		sle.pop("posting_time")
		sle.pop("voucher_detail_no")

	return sl_entries[0] if len(sl_entries) == 1 else None


def get_list_action(barcode_doc: frappe._dict, context: frappe._dict) -> list[dict[str, Any]]:
	target = barcode_doc.doc.name
	if barcode_doc.doc.doctype == "Handling Unit":
		if barcode_doc.doc.get("parenttype") == "Packing Slip":
			target = barcode_doc.doc.parent
		elif context.get("listview") == "Packing Slip" and barcode_doc.doc.parenttype != "Packing Slip":
			target = frappe.db.get_value(
				"Packing Slip Item", {"handling_unit": barcode_doc.doc.name}, "parent"
			)
		else:
			target = get_handling_unit(barcode_doc.doc.name)
			target = target.get("voucher_no") if target else None
	elif barcode_doc.doc.doctype == "Asset":
		target = barcode_doc.doc.item_code

	if not target:
		return []

	listview = {
		("Item", "Item"): [("route", "Item", "Item", target)],
		("Asset", "Item"): [
			("route", "Item", "Item", target),
		],
		("Warehouse", "Item"): [
			("filter", "Item Default", "default_warehouse", target),
		],
		("Handling Unit", "Item"): [("route", "Item", "Item", target)],
		("Item", "Asset"): [("filter", "Asset", "item_code", target)],
		("Asset", "Asset"): [("route", "Asset", "Asset", barcode_doc.doc.name)],
		("Warehouse", "Warehouse"): [("route", "Warehouse", "Warehouse", target)],
		("Item", "Purchase Receipt"): [
			("filter", "Purchase Receipt Item", "item_code", target),
		],
		("Asset", "Purchase Receipt"): [
			("filter", "Purchase Receipt Item", "item_code", target),
		],
		("Warehouse", "Purchase Receipt"): [
			("filter", "Accepted Warehouse (Purchase Receipt Item)", target),
		],
		("Handling Unit", "Purchase Receipt"): [
			("route", "Purchase Receipt", "Purchase Receipt", target)
		],
		("Item", "Purchase Invoice"): [
			("filter", "Purchase Invoice Item", "item_code", target),
		],
		("Asset", "Purchase Invoice"): [
			("filter", "Purchase Invoice Item", "item_code", target),
		],
		("Warehouse", "Purchase Invoice"): [
			("filter", "Purchase Invoice Item", "warehouse", target),
		],
		("Handling Unit", "Purchase Invoice"): [
			("route", "Purchase Invoice", "Purchase Invoice", target)
		],
		("Item", "Delivery Note"): [
			("filter", "Delivery Note Item", "item_code", target),
		],
		("Warehouse", "Delivery Note"): [
			("filter", "Delivery Note Item", "warehouse", target),
		],
		("Handling Unit", "Delivery Note"): [("route", "Delivery Note", "Delivery Note", target)],
		("Item", "Sales Invoice"): [
			("filter", "Sales Invoice Item", "item_code", target),
		],
		("Warehouse", "Sales Invoice"): [
			("filter", "Sales Invoice Item", "warehouse", target),
		],
		("Handling Unit", "Sales Invoice"): [("route", "Sales Invoice", "Sales Invoice", target)],
		("Item", "Stock Entry"): [
			("filter", "Stock Entry Detail", "item_code", target),
		],
		("Warehouse", "Stock Entry"): [
			("filter", "Stock Entry Detail", "warehouse", target),
		],
		("Handling Unit", "Stock Entry"): [("route", "Stock Entry", "Stock Entry", target)],
		("Item", "Stock Reconciliation"): [
			("filter", "Stock Reconciliation Item", "item_code", target),
		],
		("Warehouse", "Stock Reconciliation"): [
			("filter", "Stock Reconciliation Item", "warehouse", target),
		],
		("Handling Unit", "Stock Reconciliation"): [
			("route", "Stock Reconciliation", "Stock Reconciliation", target)
		],
		("Item", "Job Card"): [
			("filter", "Job Card Item", "item_code", target),
		],
		("Warehouse", "Job Card"): [
			("filter", "Job Card Item", "warehouse", target),
		],
		("Handling Unit", "Job Card"): [("route", "Job Card", "Job Card", target)],
		("Item", "Packing Slip"): [
			("filter", "Packing Slip Item", "item_code", target),
		],
		("Warehouse", "Packing Slip"): [
			("filter", "Packing Slip Item", "warehouse", target),
		],
		("Handling Unit", "Packing Slip"): [("route", "Packing Slip", "Packing Slip", target)],
	}
	return [
		{"action": l[0], "doctype": l[1], "field": l[2], "target": l[3]}
		for l in listview.get((barcode_doc.doc.doctype, context.listview))
	]


def get_form_action(barcode_doc: frappe._dict, context: frappe._dict) -> list[dict[str, Any]]:
	target = None
	if barcode_doc.doc.doctype == "Handling Unit":
		target = get_handling_unit(barcode_doc.doc.name)
	elif barcode_doc.doc.doctype == "Asset":
		target = barcode_doc.doc.item_code

	if not target:
		return []

	frm = {
		("Item", "Purchase Receipt"): [
			("add_or_increment", "Purchase Receipt Item", "item_code", target, target),
		],
		("Asset", "Purchase Receipt"): [
			("add_or_increment", "Purchase Receipt Item", "item_code", target.item_code, target),
		],
		("Warehouse", "Purchase Receipt"): [
			("set_warehouse", "Purchase Receipt Item", "warehouse", target.warehouse, target),
		],
		("Item", "Purchase Invoice"): [
			("add_or_increment", "Purchase Invoice Item", "item_code", target.item_code, target),
		],
		("Asset", "Purchase Invoice"): [
			("add_or_increment", "Purchase Invoice Item", "item_code", target.item_code, target),
		],
		("Warehouse", "Purchase Invoice"): [
			("set_warehouse", "Purchase Invoice Item", "warehouse", target.warehouse, target),
		],
		("Handling Unit", "Purchase Invoice"): [
			(
				"add_or_associate",
				"Purchase Invoice Item",
				"handling_unit",
				target.handling_unit,
				target,
			),
		],
		("Item", "Delivery Note"): [
			("add_or_increment", "Delivery Note Item", "item_code", target.item_code, target),
		],
		("Warehouse", "Delivery Note"): [
			("set_warehouse", "Delivery Note Item", "warehouse", target.warehouse, target),
		],
		("Handling Unit", "Delivery Note"): [
			(
				"add_or_associate",
				"Delivery Note Item",
				"handling_unit",
				target.handling_unit,
				target,
			),
			("add_or_associate", "Delivery Note Item", "rate", target.rate, target),
		],
		("Item", "Sales Invoice"): [
			("add_or_increment", "Sales Invoice Item", "item_code", target.item_code, target),
		],
		("Warehouse", "Sales Invoice"): [
			("set_warehouse", "Sales Invoice Item", "warehouse", target.warehouse, target),
		],
		("Handling Unit", "Sales Invoice"): [
			(
				"add_or_associate",
				"Sales Invoice Item",
				"handling_unit",
				target.handling_unit,
				target,
			),
		],
		("Item", "Stock Reconciliation"): [
			(
				"add_or_increment",
				"Stock Reconciliation Item",
				"item_code",
				target.item_code,
				target,
			),
		],
		("Warehouse", "Stock Reconciliation"): [
			(
				"set_warehouse",
				"Stock Reconciliation Item",
				"warehouse",
				target.warehouse,
				target,
			),
		],
		("Handling Unit", "Stock Reconciliation"): [
			(
				"add_or_associate",
				"Stock Reconciliation Item",
				"handling_unit",
				target.handling_unit,
				target,
			),
		],
		("Item", "Stock Entry"): [
			("add_or_increment", "Stock Entry Detail", "item_code", target.item_code, target),
		],
		("Warehouse", "Stock Entry"): [
			("set_warehouse", "Stock Entry", "warehouse", target.warehouse, target),
		],
		("Handling Unit", "Stock Entry"): [
			(
				"add_or_associate",
				"Stock Entry Detail",
				"handling_unit",
				target.handling_unit,
				target,
			),
			(
				"add_or_associate",
				"Stock Entry Detail",
				"basic_rate",
				target.valuation_rate,
				target,
			),
			("add_or_associate", "Stock Entry Detail", "s_warehouse", target.warehouse, target),
			("add_or_associate", "Stock Entry Detail", "transfer_qty", target.stock_qty, target),
			(
				"add_or_associate",
				"Stock Entry Detail",
				"conversion_factor",
				target.conversion_factor,
				target,
			),
		],
		("Item", "Job Card"): [
			("add_or_increment", "Job Card Item", "item_code", target.item_code, target),
		],
		("Handling Unit", "Job Card"): [
			("add_or_associate", "Job Card Item", "handling_unit", target.handling_unit, target),
			("add_or_associate", "Job Card Item", "pulled_qty", target.stock_qty, target),
		],
		("Handling Unit", "Packing Slip"): [
			(
				"add_or_associate",
				"Packing Slip Item",
				"handling_unit",
				target.handling_unit,
				target,
			),
			("add_or_associate", "Packing Slip Item", "rate", target.rate, target),
			("add_or_associate", "Packing Slip Item", "pulled_quantity", target.qty, target),
			("add_or_associate", "Packing Slip Item", "stock_qty", target.stock_qty, target),
			(
				"add_or_associate",
				"Packing Slip Item",
				"conversion_factor",
				target.conversion_factor,
				target,
			),
			("add_or_associate", "Packing Slip Item", "warehouse", target.warehouse, target),
		],
	}

	return [
		{
			"action": l[0],
			"doctype": l[1],
			"field": l[2],
			"target": l[3],
			"context": l[4],
		}
		for l in frm.get((barcode_doc.doc.doctype, context.frm))
	]
