import datetime
import json
from typing import Any, Optional, Union

import frappe
from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry
from erpnext.stock.get_item_details import get_item_details


@frappe.whitelist()
def scan(
	barcode: str,
	context: Optional[Union[str, dict[str, Any]]] = None,
	current_qty: Optional[Union[str, float]] = None,
) -> Union[list[dict[str, Any]], None]:
	if not context:
		context = {}  # TODO: is this the correct assumption?
	context_dict = frappe._dict(json.loads(context) if isinstance(context, str) else context)
	barcode_doc = get_barcode_context(barcode)
	if not barcode_doc:
		frappe.msgprint("Barcode not found", alert=True)
		return None  # mypy asked for this
	if "listview" in context_dict:
		return get_list_action(barcode_doc, context_dict)
	elif "frm" in context_dict:
		return get_form_action(barcode_doc, context_dict)  # TODO: add current_qty argument here
	return None  # mypy asked for this


def get_barcode_context(barcode: str) -> Union[frappe._dict, None]:
	item_barcode = frappe.db.get_value(
		"Item Barcode", {"barcode": barcode}, ["parent", "parenttype"], as_dict=True
	)
	if not item_barcode:
		return None  # mypy asked for this
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
			"SUM(actual_qty) AS stock_qty",
			"handling_unit",
			"voucher_no",
			"posting_date",
			"posting_time",
			"stock_uom",
			"voucher_type",
			"voucher_detail_no",
		],
		group_by="handling_unit",
		order_by="posting_date DESC",
		limit=1,
	)
	if len(sl_entries) == 1:
		sle = sl_entries[0]
	else:
		return

	if sle.voucher_type == "Stock Entry":
		child_doctype = "Stock Entry Detail"
	else:
		child_doctype = f"{sle.voucher_type} Item"

	_sle = frappe.db.get_value(
		child_doctype,
		sle.voucher_detail_no,
		["uom", "qty", "conversion_factor", "stock_uom", "idx", "item_name"],
		as_dict=True,
	)

	if _sle:
		sle.update({**_sle})
		sle.stock_qty = sle.stock_qty / sle.conversion_factor

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
	return sle


def get_stock_entry_item_details(doc: dict, item_code: str) -> frappe._dict:
	# the base `get_item_details` cannot handle doctypes whose items table name doesn't have
	# "Item" in it, which will fail for Stock Entry
	stock_entry = StockEntry(frappe._dict(doc))
	if not stock_entry.stock_entry_type:
		stock_entry.purpose = "Material Transfer"
		stock_entry.set_stock_entry_type()
	target = stock_entry.get_item_details({"item_code": item_code})
	target.item_code = item_code
	target.qty = 1  # only required for first scan, since quantity by default is zero
	return target


def get_list_action(barcode_doc: frappe._dict, context: frappe._dict) -> list[dict[str, Any]]:
	target = barcode_doc.doc.name
	if barcode_doc.doc.doctype == "Handling Unit":
		if barcode_doc.doc.get("parenttype") == "Packing Slip":
			# TODO: is this check correct and/or required?
			target = barcode_doc.doc.parent
		elif (
			context.get("listview") == "Packing Slip"
			and barcode_doc.doc.get("parenttype") != "Packing Slip"
		):
			target = frappe.db.get_value(
				"Packing Slip Item", {"handling_unit": barcode_doc.doc.name}, "parent"
			)
		else:
			target = get_handling_unit(barcode_doc.doc.name)
			target = target.get("voucher_no") if target else None

	if not target:
		return []

	beam_override = frappe.get_hooks("beam_listview")

	if beam_override:
		override_doctype = beam_override.get(barcode_doc.doc.doctype)
		if override_doctype:
			override_action = override_doctype.get(context.listview)
			if override_action:
				for action in override_action:
					action["context"] = target
					action["target"] = target
				return override_action

	actions = listview.get(barcode_doc.doc.doctype, {}).get(context.listview, [])
	for action in actions:
		action["context"] = target
		action["target"] = target

	return actions


def get_form_action(barcode_doc: frappe._dict, context: frappe._dict) -> list[dict[str, Any]]:
	target = None
	if barcode_doc.doc.doctype == "Handling Unit":
		hu_details = get_handling_unit(barcode_doc.doc.name)
		if context.frm == "Stock Entry":
			target = get_stock_entry_item_details(context.doc, hu_details.item_code)
		elif context.frm in ("Putaway Rule", "Warranty Claim", "Item Price", "Quality Inspection"):
			target = frappe._dict(
				{
					"doctype": context.frm,
					"item_code": hu_details.item_code,
				}
			)
		else:
			target = get_item_details(
				{
					"doctype": context.frm,
					"item_code": hu_details.item_code,
					"company": frappe.defaults.get_user_default("Company"),
					"currency": frappe.defaults.get_user_default("Currency"),
				}
			)
		target.update(
			{
				"handling_unit": hu_details.handling_unit,
				"voucher_no": hu_details.voucher_no,
				"stock_qty": hu_details.stock_qty,
				"qty": hu_details.stock_qty / target.conversion_factor
				if target.conversion_factor
				else hu_details.stock_qty,
				"posting_datetime": hu_details.posting_datetime,
			}
		)
	elif barcode_doc.doc.doctype == "Item":
		if context.frm == "Stock Entry":
			target = get_stock_entry_item_details(context.doc, barcode_doc.doc.name)
		elif context.frm in ("Putaway Rule", "Warranty Claim", "Item Price", "Quality Inspection"):
			target = frappe._dict(
				{
					"doctype": context.frm,
					"item_code": barcode_doc.doc.name,
				}
			)
		else:
			target = get_item_details(
				{
					"doctype": context.frm,
					"item_code": barcode_doc.doc.name,
					"company": frappe.defaults.get_user_default("Company"),
					"currency": frappe.defaults.get_user_default("Currency"),
				}
			)
		target.barcode = barcode_doc.barcode

	if not target:
		return []

	beam_override = frappe.get_hooks("beam_frm")

	if beam_override:
		override_doctype = beam_override.get(barcode_doc.doc.doctype)
		if override_doctype:
			override_action = override_doctype.get(context.frm)
			if override_action:
				for action in override_action:
					action["context"] = target
					if "." in action.get("target"):
						serialized_target = action.get("target").split(".")
						action["target"] = target.get(serialized_target[1])
					else:
						action["target"] = target
				return override_action

	actions = frm.get(barcode_doc.doc.doctype, {}).get(context.frm, [])
	for action in actions:
		action["context"] = target
		if isinstance(action.get("target"), str) and "." in action.get("target"):
			serialized_target = action.get("target").split(".")
			action["target"] = target.get(serialized_target[1])
		else:
			action["target"] = target

	return actions


listview = {
	"Handling Unit": {
		"Delivery Note": [
			{"action": "route", "doctype": "Delivery Note", "field": "Delivery Note", "target": "target"}
		],
		"Item": [{"action": "route", "doctype": "Item", "field": "Item", "target": "target"}],
		"Packing Slip": [
			{"action": "route", "doctype": "Packing Slip", "field": "Packing Slip", "target": "target"}
		],
		"Purchase Invoice": [
			{
				"action": "route",
				"doctype": "Purchase Invoice",
				"field": "Purchase Invoice",
				"target": "target",
			}
		],
		"Purchase Receipt": [
			{
				"action": "route",
				"doctype": "Purchase Receipt",
				"field": "Purchase Receipt",
				"target": "target",
			}
		],
		"Putaway Rule": [
			{"action": "filter", "doctype": "Putaway Rule", "field": "item_code", "target": "target"},
		],
		"Quality Inspection": [
			{
				"action": "filter",
				"doctype": "Quality Inspection",
				"field": "handling_unit",
				"target": "target",
			},
		],
		"Sales Invoice": [
			{"action": "route", "doctype": "Sales Invoice", "field": "Sales Invoice", "target": "target"}
		],
		"Stock Entry": [
			{"action": "route", "doctype": "Stock Entry", "field": "Stock Entry", "target": "target"}
		],
		"Stock Reconciliation": [
			{
				"action": "route",
				"doctype": "Stock Reconciliation",
				"field": "Stock Reconciliation",
				"target": "target",
			}
		],
	},
	"Item": {
		"Delivery Note": [
			{"action": "filter", "doctype": "Delivery Note Item", "field": "item_code", "target": "target"},
		],
		"Item": [{"action": "route", "doctype": "Item", "field": "Item", "target": "target"}],
		"Item Price": [
			{"action": "filter", "doctype": "Item Price", "field": "item_code", "target": "target"},
		],
		"Packing Slip": [
			{"action": "filter", "doctype": "Packing Slip Item", "field": "item_code", "target": "target"},
		],
		"Purchase Invoice": [
			{
				"action": "filter",
				"doctype": "Purchase Invoice Item",
				"field": "item_code",
				"target": "target",
			},
		],
		"Purchase Receipt": [
			{
				"action": "filter",
				"doctype": "Purchase Receipt Item",
				"field": "item_code",
				"target": "target",
			},
		],
		"Putaway Rule": [
			{"action": "filter", "doctype": "Putaway Rule", "field": "item_code", "target": "target"},
		],
		"Quality Inspection": [
			{"action": "filter", "doctype": "Quality Inspection", "field": "item_code", "target": "target"},
		],
		"Sales Invoice": [
			{"action": "filter", "doctype": "Sales Invoice Item", "field": "item_code", "target": "target"},
		],
		"Stock Entry": [
			{"action": "filter", "doctype": "Stock Entry Detail", "field": "item_code", "target": "target"},
		],
		"Stock Reconciliation": [
			{
				"action": "filter",
				"doctype": "Stock Reconciliation Item",
				"field": "item_code",
				"target": "target",
			},
		],
		"Warranty Claim": [
			{"action": "filter", "doctype": "Warranty Claim", "field": "item_code", "target": "target"},
		],
	},
	"Warehouse": {
		"Delivery Note": [
			{"action": "filter", "doctype": "Delivery Note Item", "field": "warehouse", "target": "target"},
		],
		"Item": [
			{
				"action": "filter",
				"doctype": "Item Default",
				"field": "default_warehouse",
				"target": "target",
			},
		],
		"Packing Slip": [
			{"action": "filter", "doctype": "Packing Slip Item", "field": "warehouse", "target": "target"},
		],
		"Purchase Invoice": [
			{
				"action": "filter",
				"doctype": "Purchase Invoice Item",
				"field": "warehouse",
				"target": "target",
			},
		],
		"Purchase Receipt": [
			{
				"action": "filter",
				"doctype": "Purchase Receipt Item",
				"field": "warehouse",
				"target": "target",
			},
		],
		"Sales Invoice": [
			{"action": "filter", "doctype": "Sales Invoice Item", "field": "warehouse", "target": "target"},
		],
		"Stock Entry": [
			{"action": "filter", "doctype": "Stock Entry Detail", "field": "warehouse", "target": "target"},
		],
		"Stock Reconciliation": [
			{
				"action": "filter",
				"doctype": "Stock Reconciliation Item",
				"field": "warehouse",
				"target": "target",
			},
		],
		"Warehouse": [
			{"action": "route", "doctype": "Warehouse", "field": "Warehouse", "target": "target"}
		],
	},
}

frm = {
	"Handling Unit": {
		"Delivery Note": [
			{
				"action": "add_or_associate",
				"doctype": "Delivery Note Item",
				"field": "handling_unit",
				"target": "target.handling_unit",
				"context": "target",
			},
			{
				"action": "add_or_associate",
				"doctype": "Delivery Note Item",
				"field": "rate",
				"target": "target.rate",
				"context": "target",
			},
		],
		"Item Price": [
			{
				"action": "set_item_code_and_handling_unit",
				"doctype": "Item Price",
				"field": "item_code",
				"target": "target.item_code",
				"context": "target",
			},
		],
		"Packing Slip": [
			{
				"action": "add_or_associate",
				"doctype": "Packing Slip Item",
				"field": "conversion_factor",
				"target": "target.conversion_factor",
				"context": "target",
			},
			{
				"action": "add_or_associate",
				"doctype": "Packing Slip Item",
				"field": "handling_unit",
				"target": "target.handling_unit",
				"context": "target",
			},
			{
				"action": "add_or_associate",
				"doctype": "Packing Slip Item",
				"field": "pulled_quantity",
				"target": "target.qty",
				"context": "target",
			},
			{
				"action": "add_or_associate",
				"doctype": "Packing Slip Item",
				"field": "rate",
				"target": "target.rate",
				"context": "target",
			},
			{
				"action": "add_or_associate",
				"doctype": "Packing Slip Item",
				"field": "stock_qty",
				"target": "target.stock_qty",
				"context": "target",
			},
			{
				"action": "add_or_associate",
				"doctype": "Packing Slip Item",
				"field": "warehouse",
				"target": "target.warehouse",
				"context": "target",
			},
		],
		"Purchase Invoice": [
			{
				"action": "add_or_associate",
				"doctype": "Purchase Invoice Item",
				"field": "handling_unit",
				"target": "target.handling_unit",
				"context": "target",
			},
		],
		"Putaway Rule": [
			{
				"action": "set_item_code_and_handling_unit",
				"doctype": "Putaway Rule",
				"field": "item_code",
				"target": "target.item_code",
				"context": "target",
			},
		],
		"Quality Inspection": [
			{
				"action": "set_item_code_and_handling_unit",
				"doctype": "Quality Inspection",
				"field": "item_code",
				"target": "target.item_code",
				"context": "target",
			},
			{
				"action": "set_item_code_and_handling_unit",
				"doctype": "Quality Inspection",
				"field": "handling_unit",
				"target": "target.handling_unit",
				"context": "target",
			},
		],
		"Sales Invoice": [
			{
				"action": "add_or_associate",
				"doctype": "Sales Invoice Item",
				"field": "handling_unit",
				"target": "target.handling_unit",
				"context": "target",
			},
		],
		"Stock Entry": [
			{
				"action": "add_or_associate",
				"doctype": "Stock Entry Detail",
				"field": "basic_rate",
				"target": "target.valuation_rate",
				"context": "target",
			},
			{
				"action": "add_or_associate",
				"doctype": "Stock Entry Detail",
				"field": "conversion_factor",
				"target": "target.conversion_factor",
				"context": "target",
			},
			{
				"action": "add_or_associate",
				"doctype": "Stock Entry Detail",
				"field": "handling_unit",
				"target": "target.handling_unit",
				"context": "target",
			},
			{
				"action": "add_or_associate",
				"doctype": "Stock Entry Detail",
				"field": "s_warehouse",
				"target": "target.warehouse",
				"context": "target",
			},
			{
				"action": "add_or_associate",
				"doctype": "Stock Entry Detail",
				"field": "transfer_qty",
				"target": "target.stock_qty",
				"context": "target",
			},
		],
		"Stock Reconciliation": [
			{
				"action": "add_or_associate",
				"doctype": "Stock Reconciliation Item",
				"field": "handling_unit",
				"target": "target.handling_unit",
				"context": "target",
			},
		],
		"Warranty Claim": [
			{
				"action": "set_item_code_and_handling_unit",
				"doctype": "Warranty Claim",
				"field": "item_code",
				"target": "target.item_code",
				"context": "target",
			},
			{
				"action": "set_item_code_and_handling_unit",
				"doctype": "Warranty Claim",
				"field": "handling_unit",
				"target": "target.handling_unit",
				"context": "target",
			},
		],
	},
	"Item": {
		"Delivery Note": [
			{
				"action": "add_or_increment",
				"doctype": "Delivery Note Item",
				"field": "item_code",
				"target": "target.item_code",
				"context": "target",
			},
		],
		"Item Price": [
			{
				"action": "set_item_code_and_handling_unit",
				"doctype": "Item Price",
				"field": "item_code",
				"target": "target.item_code",
				"context": "target",
			},
		],
		"Packing Slip": [
			{
				"action": "add_or_increment",
				"doctype": "Packing Slip Item",
				"field": "item_code",
				"target": "target.item_code",
				"context": "target",
			},
		],
		"Purchase Invoice": [
			{
				"action": "add_or_increment",
				"doctype": "Purchase Invoice Item",
				"field": "item_code",
				"target": "target.item_code",
				"context": "target",
			},
		],
		"Purchase Receipt": [
			{
				"action": "add_or_increment",
				"doctype": "Purchase Receipt Item",
				"field": "item_code",
				"target": "target.item_code",
				"context": "target",
			},
		],
		"Putaway Rule": [
			{
				"action": "set_item_code_and_handling_unit",
				"doctype": "Putaway Rule",
				"field": "item_code",
				"target": "target.item_code",
				"context": "target",
			},
		],
		"Quality Inspection": [
			{
				"action": "set_item_code_and_handling_unit",
				"doctype": "Quality Inspection",
				"field": "item_code",
				"target": "target.item_code",
				"context": "target",
			},
		],
		"Sales Invoice": [
			{
				"action": "add_or_increment",
				"doctype": "Sales Invoice Item",
				"field": "item_code",
				"target": "target.item_code",
				"context": "target",
			},
		],
		"Stock Entry": [
			{
				"action": "add_or_increment",
				"doctype": "Stock Entry Detail",
				"field": "item_code",
				"target": "target.item_code",
				"context": "target",
			},
		],
		"Stock Reconciliation": [
			{
				"action": "add_or_increment",
				"doctype": "Stock Reconciliation Item",
				"field": "item_code",
				"target": "target.item_code",
				"context": "target",
			},
		],
		"Warranty Claim": [
			{
				"action": "set_item_code_and_handling_unit",
				"doctype": "Warranty Claim",
				"field": "item_code",
				"target": "target.item_code",
				"context": "target",
			},
		],
	},
	"Warehouse": {
		"Delivery Note": [
			{
				"action": "set_warehouse",
				"doctype": "Delivery Note Item",
				"field": "warehouse",
				"target": "target.warehouse",
				"context": "target",
			},
		],
		"Purchase Invoice": [
			{
				"action": "set_warehouse",
				"doctype": "Purchase Invoice Item",
				"field": "warehouse",
				"target": "target.warehouse",
				"context": "target",
			},
		],
		"Purchase Receipt": [
			{
				"action": "set_warehouse",
				"doctype": "Purchase Receipt Item",
				"field": "warehouse",
				"target": "target.warehouse",
				"context": "target",
			},
		],
		"Sales Invoice": [
			{
				"action": "set_warehouse",
				"doctype": "Sales Invoice Item",
				"field": "warehouse",
				"target": "target.warehouse",
				"context": "target",
			},
		],
		"Stock Entry": [
			{
				"action": "set_warehouse",
				"doctype": "Stock Entry",
				"field": "warehouse",
				"target": "target.warehouse",
				"context": "target",
			},
		],
		"Stock Reconciliation": [
			{
				"action": "set_warehouse",
				"doctype": "Stock Reconciliation Item",
				"field": "warehouse",
				"target": "target.warehouse",
				"context": "target",
			},
		],
	},
}
