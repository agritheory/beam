# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import copy
import datetime
import json
from typing import Any

import frappe
from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry
from erpnext.stock.get_item_details import get_item_details, get_valuation_rate
from frappe.query_builder import Case, DocType
from frappe.query_builder.custom import ConstantColumn
from frappe.query_builder.functions import Coalesce


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
		return None  # mypy asked for this
	# print(barcode_doc.as_json())
	if "listview" in context_dict:
		return get_list_action(barcode_doc, context_dict)
	elif "frm" in context_dict:
		return get_form_action(barcode_doc, context_dict)  # TODO: add current_qty argument here
	return None  # mypy asked for this


def get_barcode_context(barcode: str) -> frappe._dict | None:
	# Get BEAM Settings for default company
	company = frappe.defaults.get_defaults().get("company")
	settings = None
	if company and frappe.db.exists("BEAM Settings", {"company": company}):
		settings = frappe.get_cached_doc("BEAM Settings", company)

	item_barcode = frappe.db.get_value(
		"Item Barcode", {"barcode": barcode}, ["parent", "parenttype"], as_dict=True
	)
	if item_barcode:
		return frappe._dict(
			{
				"doc": frappe.get_doc(item_barcode.parenttype, item_barcode.parent),
				"barcode": barcode,
			}
		)
	elif not item_barcode and settings and settings.scan_serial_no:
		serial_no_table = frappe.qb.DocType("Serial No")
		bundle_entry_table = frappe.qb.DocType("Serial and Batch Entry")
		bundle_table = frappe.qb.DocType("Serial and Batch Bundle")
		serial_lookup = (
			(
				frappe.qb.from_(serial_no_table)
				.select(
					ConstantColumn("Serial No").as_("doctype"),
					serial_no_table.name,
				)
				.where(serial_no_table.name == barcode)
			)
			.union(
				frappe.qb.from_(bundle_entry_table)
				.join(bundle_table)
				.on(bundle_entry_table.parent == bundle_table.name)
				.select(
					ConstantColumn("Serial and Batch Bundle").as_("doctype"),
					bundle_entry_table.parent,
				)
				.where(bundle_entry_table.serial_no == barcode)
			)
			.limit(1)
			.run(as_dict=True)
		)
		if serial_lookup:
			return frappe._dict(
				{
					"doc": frappe.get_doc(serial_lookup[0].doctype, serial_lookup[0].name),
					"barcode": barcode,
				}
			)

	# Fallback: custom barcode resolvers registered by other apps via beam_barcode_resolver hook
	for resolver in frappe.get_hooks("beam_barcode_resolver"):
		result = frappe.call(resolver, barcode=barcode)
		if result:
			return result

	return None


def get_handling_unit(handling_unit: str, parent_doctype: str | None = None) -> frappe._dict:
	if not handling_unit:
		return

	sl_entries = frappe.get_all(
		"Stock Ledger Entry",
		filters={"handling_unit": handling_unit, "is_cancelled": 0},
		fields=[
			"item_code",
			"SUM(actual_qty) AS stock_qty",
			"company",
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
	elif barcode_doc.doc.doctype == "Serial No":
		if context.get("listview") in ["Item", "Putaway Rule"]:
			target = barcode_doc.doc.item_code
		else:
			target = get_serial_no(barcode_doc.doc.name, context.get("listview"))
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
					if callable(action.get("target")):
						target_fn = action.get("target")
						target = target_fn(barcode_doc, context)
					action["context"] = target
					action["target"] = target
					if action.get("action") == "route":
						action["route"] = action.get("route").format(target=target)
				return override_action

	# avoid mutating the global `listview` dict
	list_actions = copy.deepcopy(listview)
	actions = list_actions.get(barcode_doc.doc.doctype, {}).get(context.listview, [])
	for action in actions:
		action["context"] = target
		action["target"] = target
		action["parent"] = barcode_doc.doc.name
		action["parenttype"] = barcode_doc.doc.doctype

	return actions


def set_item_stock_uom(target: frappe._dict, item_code: str) -> None:
	stock_uom = frappe.get_cached_value("Item", item_code, "stock_uom")
	if stock_uom:
		target.uom = stock_uom
		target.stock_uom = stock_uom


def get_form_action(barcode_doc: frappe._dict, context: frappe._dict) -> list[dict[str, Any]]:
	target = None
	beam_override = frappe.get_hooks("beam_frm")
	has_frm_override = bool(
		beam_override and beam_override.get(barcode_doc.doc.doctype, {}).get(context.frm)
	)

	if barcode_doc.doc.doctype == "Handling Unit":
		hu_details = get_handling_unit(barcode_doc.doc.name, context.frm)
		if context.frm == "Stock Entry":
			if not context.doc:
				context.doc = {"doctype": "Stock Entry"}
			target = get_stock_entry_item_details(context.doc, hu_details.item_code)
			target.warehouse = hu_details.warehouse
		elif context.frm in ("Putaway Rule", "Warranty Claim", "Item Price", "Quality Inspection"):
			target = frappe._dict(
				{
					"doctype": context.frm,
					"item_code": hu_details.item_code,
				}
			)
		elif has_frm_override:
			# A beam_frm override handles this form — skip get_item_details() which would
			# fail for forms without a standard "{doctype} Item" child table.
			target = frappe._dict(
				{
					"doctype": context.frm,
					"item_code": hu_details.item_code,
				}
			)
			set_item_stock_uom(target, hu_details.item_code)
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
	elif barcode_doc.doc.doctype == "Item" and context.doc:
		if context.frm == "Stock Entry":
			target = get_stock_entry_item_details(context.doc, barcode_doc.doc.name)
		elif context.frm in ("Putaway Rule", "Warranty Claim", "Item Price", "Quality Inspection"):
			target = frappe._dict(
				{
					"doctype": context.frm,
					"item_code": barcode_doc.doc.name,
				}
			)
		elif has_frm_override:
			# A beam_frm override handles this form — skip get_item_details() which would
			# fail for forms without a standard "{doctype} Item" child table.
			target = frappe._dict(
				{
					"doctype": context.frm,
					"item_code": barcode_doc.doc.name,
				}
			)
			set_item_stock_uom(target, barcode_doc.doc.name)
		else:
			target = get_item_details(
				{
					"doctype": context.frm,
					"item_code": barcode_doc.doc.name,
					"company": frappe.defaults.get_user_default("Company"),
					"currency": frappe.defaults.get_user_default("Currency"),
				}
			)
			valuation_rate = get_valuation_rate(barcode_doc.doc.name, target.company, target.warehouse)
			if valuation_rate.get("valuation_rate"):
				target.valuation_rate = valuation_rate.valuation_rate
		target.barcode = barcode_doc.barcode
	elif barcode_doc.doc.doctype == "Warehouse" and context.frm == "Stock Reconciliation":
		target = frappe._dict(
			{
				"doctype": context.frm,
				"warehouse": barcode_doc.doc.name,
			}
		)
		target.barcode = barcode_doc.barcode
	elif barcode_doc.doc.doctype == "Serial No":
		serial_no_details = get_serial_no(barcode_doc.doc.name, context.frm)
		if context.frm == "Stock Entry":
			target = get_stock_entry_item_details(context.doc, serial_no_details.item_code)
			target.warehouse = serial_no_details.warehouse
		elif context.frm in ("Putaway Rule", "Warranty Claim", "Item Price", "Quality Inspection"):
			target = frappe._dict(
				{
					"doctype": context.frm,
					"item_code": serial_no_details.item_code,
				}
			)
		else:
			target = get_item_details(
				{
					"doctype": context.frm,
					"item_code": serial_no_details.item_code,
					"company": frappe.defaults.get_user_default("Company"),
					"currency": frappe.defaults.get_user_default("Currency"),
				}
			)
		target.update(
			{
				"handling_unit": serial_no_details.handling_unit,
				"voucher_no": serial_no_details.voucher_no,
				"stock_qty": serial_no_details.stock_qty,
				"qty": serial_no_details.stock_qty / target.conversion_factor
				if target.conversion_factor
				else serial_no_details.stock_qty,
				"posting_datetime": serial_no_details.posting_datetime,
				"dn_detail": serial_no_details.dn_detail,
			}
		)
	else:
		target = frappe._dict(**barcode_doc)

	if not target:
		return []

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

	# avoid mutating the global `frm` dict
	form_actions = copy.deepcopy(frm)
	actions = form_actions.get(barcode_doc.doc.doctype, {}).get(context.frm, [])
	for action in actions:
		action["context"] = target
		target_value = action.get("target")
		if isinstance(target_value, str) and "." in target_value:
			serialized_target = target_value.split(".")
			action["target"] = target.get(serialized_target[1])

	return actions


def get_serial_no(serial_no: str, parent_doctype: str | None = None) -> frappe._dict:
	sle = DocType("Stock Ledger Entry")
	snb = DocType("Serial and Batch Entry")
	snb_bundle = DocType("Serial and Batch Bundle")
	se_detail = DocType("Stock Entry Detail")
	pr_item = DocType("Purchase Receipt Item")
	pi_item = DocType("Purchase Invoice Item")
	dn_item = DocType("Delivery Note Item")

	main_query = (
		frappe.qb.from_(sle)
		.left_join(snb_bundle)
		.on(sle.serial_and_batch_bundle == snb_bundle.name)
		.left_join(snb)
		.on(snb_bundle.name == snb.parent)
		.left_join(se_detail)
		.on((sle.voucher_type == "Stock Entry") & (sle.voucher_detail_no == se_detail.name))
		.left_join(pr_item)
		.on((sle.voucher_type == "Purchase Receipt") & (sle.voucher_detail_no == pr_item.name))
		.left_join(pi_item)
		.on((sle.voucher_type == "Purchase Invoice") & (sle.voucher_detail_no == pi_item.name))
		.left_join(dn_item)
		.on((sle.voucher_type == "Delivery Note") & (sle.voucher_detail_no == dn_item.name))
		.select(
			sle.item_code,
			sle.actual_qty.as_("stock_qty"),
			sle.company,
			sle.voucher_no,
			sle.posting_date,
			sle.posting_time,
			sle.stock_uom,
			sle.voucher_type,
			sle.voucher_detail_no,
			sle.warehouse,
			sle.serial_and_batch_bundle,
			Coalesce(snb.serial_no, sle.serial_no).as_("serial_no"),
			# Item details from whichever child table matches
			Coalesce(se_detail.uom, pr_item.uom, pi_item.uom, dn_item.uom).as_("uom"),
			Coalesce(se_detail.qty, pr_item.qty, pi_item.qty, dn_item.qty).as_("qty"),
			Coalesce(
				se_detail.conversion_factor,
				pr_item.conversion_factor,
				pi_item.conversion_factor,
				dn_item.conversion_factor,
			).as_("conversion_factor"),
			Coalesce(se_detail.idx, pr_item.idx, pi_item.idx, dn_item.idx).as_("idx"),
			Coalesce(se_detail.item_name, pr_item.item_name, pi_item.item_name, dn_item.item_name).as_(
				"item_name"
			),
			Coalesce(se_detail.name, pr_item.name, pi_item.name, dn_item.name).as_("detail_name"),
			# Special field for Purchase Receipt
			Case()
			.when(sle.voucher_type == "Purchase Receipt", pr_item.stock_qty)
			.else_(None)
			.as_("stock_qty_field"),
			# For Packing Slip case - get delivery note item details
			Case()
			.when(
				(dn_item.docstatus == 0)
				& ((snb.serial_no == serial_no) | (dn_item.serial_no.like(f"%{serial_no}%"))),
				dn_item.name,
			)
			.else_(None)
			.as_("dn_detail"),
		)
		.where(
			(sle.is_cancelled == 0)
			& (
				(snb.serial_no == serial_no)
				| (sle.serial_no.like(f"%{serial_no}%"))  # Serial and Batch method  # Direct field method
			)
		)
		.groupby(sle.voucher_no, sle.voucher_detail_no)
		.orderby(sle.posting_date, order=frappe.qb.desc)
		.orderby(sle.posting_time, order=frappe.qb.desc)
		.limit(1)
	)

	result = main_query.run(as_dict=True)

	if not result:
		return

	sle_data = frappe._dict(result[0])

	if sle_data.stock_qty_field is not None:
		sle_data.stock_qty = sle_data.stock_qty_field

	if parent_doctype == "Packing Slip" and sle_data.dn_detail:
		sle_data.dn_detail = sle_data.dn_detail

	sle_data.qty = 1.0

	if sle_data.conversion_factor and sle_data.conversion_factor != 0:
		sle_data.stock_qty = sle_data.qty / sle_data.conversion_factor
	else:
		sle_data.stock_qty = sle_data.qty

	sle_data.posting_datetime = (
		datetime.datetime(
			sle_data.posting_date.year, sle_data.posting_date.month, sle_data.posting_date.day
		)
		+ sle_data.posting_time
	)

	sle_data.user = frappe.session.user
	sle_data.pop("posting_date", None)
	sle_data.pop("posting_time", None)
	sle_data.pop("voucher_detail_no", None)
	sle_data.pop("stock_qty_field", None)
	sle_data.pop("detail_name", None)

	return sle_data


listview = {
	"Handling Unit": {
		"Delivery Note": [
			{"action": "filter", "doctype": "Delivery Note", "field": "name", "target": "target"}
		],
		"Item": [{"action": "route", "doctype": "Item", "field": "Item", "target": "target"}],
		"Packing Slip": [
			{"action": "filter", "doctype": "Packing Slip", "field": "name", "target": "target"}
		],
		"Purchase Invoice": [
			{
				"action": "filter",
				"doctype": "Purchase Invoice",
				"field": "name",
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
			{"action": "filter", "doctype": "Sales Invoice", "field": "name", "target": "target"}
		],
		"Stock Entry": [
			{"action": "filter", "doctype": "Stock Entry", "field": "name", "target": "target"}
		],
		"Stock Reconciliation": [
			{
				"action": "filter",
				"doctype": "Stock Reconciliation",
				"field": "name",
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
	"Serial No": {
		"Delivery Note": [
			{"action": "filter", "doctype": "Delivery Note", "field": "name", "target": "target"}
		],
		"Item": [{"action": "route", "doctype": "Item", "field": "Item", "target": "target"}],
		"Packing Slip": [
			{"action": "filter", "doctype": "Packing Slip", "field": "name", "target": "target"}
		],
		"Purchase Invoice": [
			{
				"action": "filter",
				"doctype": "Purchase Invoice",
				"field": "name",
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
		"Stock Entry": [
			{"action": "filter", "doctype": "Stock Entry", "field": "name", "target": "target"}
		],
		"Stock Reconciliation": [
			{
				"action": "filter",
				"doctype": "Stock Reconciliation",
				"field": "name",
				"target": "target",
			}
		],
	},
}

frm = {
	"Handling Unit": {
		"Work Order": [
			{
				"action": "add_or_associate",
				"doctype": "Stock Entry",
				"field": "handling_unit",
				"target": "target.handling_unit",
				"context": "target",
			},
			{
				"action": "add_or_associate",
				"doctype": "Stock Entry",
				"field": "qty",
				"target": "target.qty",
				"context": "target",
			},
		],
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
				"field": "delivered_qty",
				"target": "target.qty",
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
			{
				"action": "add_or_associate",
				"doctype": "Packing Slip Item",
				"field": "dn_detail",
				"target": "target.dn_detail",
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
		"Work Order": [
			{
				"action": "add_or_increment",
				"doctype": "Stock Entry",
				"field": "item_code",
				"target": "target.item_code",
				"context": "target",
			},
		],
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
	"Serial No": {
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
			{
				"action": "add_or_associate",
				"doctype": "Packing Slip Item",
				"field": "dn_detail",
				"target": "target.dn_detail",
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
}
