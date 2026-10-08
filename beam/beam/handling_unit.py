# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt


import frappe
from erpnext.stock.doctype.inventory_dimension.inventory_dimension import get_inventory_dimensions
from erpnext.stock.doctype.serial_no.serial_no import get_serial_nos as get_parsed_serial_nos
from erpnext.stock.serial_batch_bundle import get_serial_nos as get_bundle_serial_nos
from erpnext.stock.stock_ledger import NegativeStockError
from erpnext.stock.utils import get_combine_datetime

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
		is_stock_item, enable_handling_unit = frappe.get_value(
			"Item", row.item_code, ["is_stock_item", "enable_handling_unit"]
		)
		if not (is_stock_item and enable_handling_unit):
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

		if (
			doc.doctype == "Stock Entry"
			and doc.purpose == "Repack"
			and row.t_warehouse
			and not row.handling_unit
		):
			handling_unit = frappe.new_doc("Handling Unit")
			handling_unit.save()
			row.handling_unit = handling_unit.name
			continue

		if doc.doctype == "Subcontracting Receipt" and not row.handling_unit:
			handling_unit = frappe.new_doc("Handling Unit")
			handling_unit.save()
			row.handling_unit = handling_unit.name

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
def set_outbound_handling_units(doc, method=None):
	"""Fill `handling_unit` on serialized Delivery Note / Sales Invoice rows so the
	outbound movement keeps the dimension ERPNext's
	validate_serial_no_inventory_dimension checks. Only when unambiguous: every serial
	on the row shares one non-empty handling unit.
	"""
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

	posting_datetime = get_combine_datetime(doc.posting_date, doc.posting_time)

	for row in doc.items:
		if row.get("handling_unit"):
			continue

		serial_nos = row_serial_nos(row)
		if not serial_nos:
			continue

		handling_unit = common_inward_handling_unit(row.item_code, serial_nos, posting_datetime)
		if handling_unit:
			row.handling_unit = handling_unit

	return doc


def row_serial_nos(row):
	if row.get("serial_and_batch_bundle"):
		return get_bundle_serial_nos(row.serial_and_batch_bundle)
	if row.get("serial_no"):
		return get_parsed_serial_nos(row.serial_no)
	return []


def common_inward_handling_unit(item_code, serial_nos, posting_datetime):
	"""The handling unit shared by every serial's last inward movement (at or before
	`posting_datetime`), or None when a serial has none, they disagree, or the
	shared value is empty.
	"""
	by_serial = last_inward_handling_units(item_code, serial_nos, posting_datetime)
	if len(by_serial) != len(set(serial_nos)):
		return None
	values = set(by_serial.values())
	if len(values) != 1:
		return None
	return next(iter(values)) or None


def last_inward_handling_units(item_code, serial_nos, posting_datetime):
	"""`{serial_no: handling_unit}` via ERPNext's `get_last_inward_dimensions` — the
	same lookup `validate_serial_no_inventory_dimension` runs, so beam resolves what
	ERPNext checks (and breaks loudly if that method changes).
	"""
	dimensions = [d for d in get_inventory_dimensions() if d.fieldname == "handling_unit"]
	if not dimensions:
		return {}

	sle = frappe.new_doc("Stock Ledger Entry")
	sle.item_code = item_code
	sle.posting_datetime = posting_datetime
	return {
		serial_no: row.get("handling_unit")
		for serial_no, row in sle.get_last_inward_dimensions(serial_nos, dimensions).items()
	}


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

	qty_field = "transfer_qty" if doc.doctype == "Stock Entry" else "stock_qty"

	for row in doc.get("items"):
		error = False
		if not hasattr(row, "handling_unit") or not row.handling_unit:
			continue

		hu = get_handling_unit(row.handling_unit)
		if not hu:
			continue

		precision_denominator = 1 / pow(100, frappe.get_precision(row.doctype, qty_field))

		if doc.doctype == "Stock Entry":
			# outgoing
			if row.get("t_warehouse") and not row.get("s_warehouse"):
				if (
					abs(hu.stock_qty - row.get(qty_field)) > 0.0
					and (hu.stock_qty - row.get(qty_field) > precision_denominator)
					and not row.is_scrap_item
				):
					error = True
			else:  # incoming and transfer / same warehouse
				if (
					abs(hu.stock_qty - row.get(qty_field)) > 0.0
					and hu.stock_qty - row.get(qty_field) < precision_denominator
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
					f"Row #{row.idx}: Handling Unit for {row.item_code} cannot be more than {hu.stock_qty:.1f} {hu.stock_uom}. You have {row.get(qty_field):.1f} {row.stock_uom}"
				),
				NegativeStockError,
				title=frappe._("Insufficient Stock"),
			)

	return doc
