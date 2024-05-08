import datetime
import json
from pathlib import Path
from typing import Any

import frappe
from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry
from erpnext.stock.get_item_details import get_item_details


@frappe.whitelist()
def scan(
	barcode: str,
	context: str | dict[str, Any] | None = None,
	current_qty: str | float | None = None,
) -> list[dict[str, Any]] | None:
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


def get_barcode_context(barcode: str) -> frappe._dict | None:
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


def get_handling_unit(handling_unit: str, parent_doctype: str | None = None) -> frappe._dict:
	sl_entries = frappe.get_all(
		"Stock Ledger Entry",
		filters={"handling_unit": handling_unit, "is_cancelled": 0},
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
			"warehouse",
		],
		group_by="handling_unit",
		order_by="posting_date DESC",
		limit=1,
	)
	if len(sl_entries) == 1:
		sle = sl_entries[0]
	else:
		return  # no entries exist

	child_doctype = (
		"Stock Entry Detail" if sle.voucher_type == "Stock Entry" else f"{sle.voucher_type} Item"
	)

	child_doctype_fields = ["uom", "qty", "conversion_factor", "idx", "item_name", "name"]

	if child_doctype == "Purchase Receipt Item":
		child_doctype_fields.append("stock_qty")

	item = frappe.db.get_value(
		child_doctype,
		sle.voucher_detail_no,
		child_doctype_fields,
		as_dict=True,
	)

	if parent_doctype == "Packing Slip":
		delivery_note_item = frappe.get_all(
			"Delivery Note Item", {"handling_unit": handling_unit, "docstatus": 0}, pluck="name"
		)
		if delivery_note_item:
			sle.dn_detail = delivery_note_item[0]

	if item:
		sle.update({**item})
		sle.qty = (
			sle.stock_qty / sle.conversion_factor
		)  # use conversion factor based on transaction not current conversion factor

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

	list_path = Path(__file__).parent / "list.json"
	LISTVIEW_ACTIONS: dict[str, dict[str, list[dict[str, str]]]] = json.loads(list_path.read_text())
	actions = LISTVIEW_ACTIONS.get(barcode_doc.doc.doctype, {}).get(context.listview, [])
	for action in actions:
		action["context"] = target
		action["target"] = target

	return actions


def get_form_action(barcode_doc: frappe._dict, context: frappe._dict) -> list[dict[str, Any]]:
	target = None
	if barcode_doc.doc.doctype == "Handling Unit":
		hu_details = get_handling_unit(barcode_doc.doc.name, context.frm)
		if context.frm == "Stock Entry":
			target = get_stock_entry_item_details(context.doc, hu_details.item_code)
			target.warehouse = hu_details.warehouse
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
				"dn_detail": hu_details.dn_detail,
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
				return override_action

	form_path = Path(__file__).parent / "form.json"
	FORMVIEW_ACTIONS: dict[str, dict[str, list[dict[str, str]]]] = json.loads(form_path.read_text())
	actions = FORMVIEW_ACTIONS.get(barcode_doc.doc.doctype, {}).get(context.frm, [])
	for action in actions:
		action["context"] = target
		if isinstance(action.get("target"), str) and "." in action.get("target"):
			serialized_target = action.get("target").split(".")
			action["target"] = target.get(serialized_target[1])

	return actions
