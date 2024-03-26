import json

import frappe
from erpnext.stock.stock_ledger import NegativeStockError

from beam.beam.doctype.beam_settings.beam_settings import create_beam_settings
from beam.beam.scan import get_handling_unit

"""
See docs/handling_unit.md
"""


@frappe.whitelist()
def generate_handling_units(doc, method=None):
	company = doc.get("company") or frappe.defaults.get_defaults().company
	settings = (
		create_beam_settings(company)
		if not frappe.db.exists("BEAM Settings", {"company": company})
		else frappe.get_doc("BEAM Settings", {"company": company})
	)

	if not settings.enable_handling_units:
		return doc

	if doc.doctype == "Purchase Invoice" and not doc.update_stock:
		return doc

	if doc.doctype == "Stock Entry" and doc.purpose == "Material Issue":
		return doc

	for row in doc.items:
		if not frappe.get_value("Item", row.item_code, "is_stock_item"):
			continue

		if (
			doc.doctype == "Stock Entry"
			and doc.purpose
			in ("Material Transfer", "Send to Subcontractor", "Material Transfer for Manufacture")
			and row.handling_unit
		):
			handling_unit = frappe.new_doc("Handling Unit")
			handling_unit.save()
			row.to_handling_unit = handling_unit.name
			continue

		if doc.doctype == "Stock Entry" and doc.purpose == "Manufacture" and row.is_scrap_item:
			create_handling_unit = frappe.get_value(
				"BOM Scrap Item", {"item_code": row.item_code, "parent": doc.bom_no}, "create_handling_unit"
			)
			if bool(create_handling_unit):
				handling_unit = frappe.new_doc("Handling Unit")
				handling_unit.save()
				row.handling_unit = handling_unit.name
			continue

		if row.get("handling_unit"):
			continue

		if doc.doctype == "Stock Entry" and not (
			any([row.is_finished_item, doc.purpose == "Material Receipt", row.is_scrap_item])
		):
			continue

		handling_unit = frappe.new_doc("Handling Unit")
		handling_unit.save()
		row.handling_unit = handling_unit.name

	return doc


@frappe.whitelist()
def validate_handling_unit_overconsumption(doc, method=None):
	company = doc.get("company") or frappe.defaults.get_defaults().company
	settings = (
		create_beam_settings(company)
		if not frappe.db.exists("BEAM Settings", {"company": company})
		else frappe.get_doc("BEAM Settings", {"company": company})
	)

	if not settings.enable_handling_units:
		return doc

	if doc.doctype == "Sales Invoice" and not doc.update_stock:
		return doc

	if doc.doctype == "Purchase Receipt" and not doc.is_return:
		return doc

	if doc.doctype == "Stock Entry" and doc.purpose == "Material Receipt":
		return doc

	qty_field = "actual_qty" if doc.doctype == "Stock Entry" else "stock_qty"

	for row in doc.get("items"):
		error = False
		if not hasattr(row, "handling_unit") or not row.handling_unit:
			continue

		hu = get_handling_unit(row.handling_unit)
		if not hu:
			continue

		precision_denominator = 1 / pow(100, frappe.get_precision(row.doctype, qty_field))

		if doc.doctype == "Stock Entry":
			# incoming
			if row.get("s_warehouse") and not row.get("t_warehouse"):
				if abs(row.get(qty_field) - hu.stock_qty) != 0.0 and (
					(row.get(qty_field) - hu.stock_qty) < precision_denominator
				):
					error = True
			# outgoing
			elif row.get("t_warehouse") and not row.get("s_warehouse"):
				if (
					abs(hu.stock_qty - row.get(qty_field)) != 0.0
					and (hu.stock_qty - row.get(qty_field) > precision_denominator)
					and not row.is_scrap_item
				):
					error = True
			else:  # transfer / same warehouse
				if abs(hu.stock_qty - row.get(qty_field)) != 0.0 and (
					hu.stock_qty - row.get(qty_field) < precision_denominator
				):
					error = True

		elif doc.doctype in ("Sales Invoice", "Delivery Note"):
			if abs(hu.stock_qty - row.get(qty_field)) != 0.0 and (
				hu.stock_qty - row.get(qty_field) < precision_denominator
			):
				error = True

		if error == True:
			frappe.throw(
				frappe._(
					f"Row #{row.idx}: Handling Unit for {row.item_code} cannot be more than {hu.stock_qty} {hu.stock_uom}. You have {row.get(qty_field)} {row.stock_uom}"
				),
				NegativeStockError,
				title=frappe._("Insufficient Stock"),
			)

	return doc
