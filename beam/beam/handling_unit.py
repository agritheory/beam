import frappe
from frappe import _

from beam.beam.scan import get_handling_unit

"""
Handling Units will be generated in the following cases:
- On all inventoriable items in a Purchase Receipt
- On all inventoriable items in a Purchase Invoice marked "Updated Stock"
- On all inventoriable items in Stock Entries of type "Material Receipt"
- On all inventoriable items in Stock Entries of type "Manufacture" or "Repack"
for scrap and finished goods items
"""


@frappe.whitelist()
def generate_handling_units(doc, method=None):
	if doc.doctype == "Purchase Invoice" and not doc.update_stock:
		return doc
	if doc.doctype == "Stock Entry" and doc.purpose not in (
		"Material Receipt",
		"Manufacture",
		"Repack",
		"Send to Subcontractor",
	):
		return doc
	for row in doc.items:
		if not frappe.get_value("Item", row.item_code, "is_stock_item"):
			continue

		if doc.doctype == "Stock Entry" and doc.purpose == "Send to Subcontractor" and row.handling_unit:
			handling_unit = frappe.new_doc("Handling Unit")
			handling_unit.save()
			row.to_handling_unit = handling_unit.name
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
	if doc.doctype == "Sales Invoice" and not doc.update_stock:
		return doc

	if doc.doctype == "Purchase Receipt" and not doc.is_return:
		return doc

	if doc.doctype == "Stock Entry" and doc.purpose not in (
		"Material Issue",
		"Material Transfer",
		"Material Transfer for Manufacture",
		"Manufacture",
		"Repack",
		"Send to Subcontractor",
		"Material Consumption for Manufacture",
	):
		return doc

	if doc.doctype == "Stock Entry":
		qty_field = "actual_qty"
	else:
		qty_field = "stock_qty"

	for row in doc.get("items"):
		if not hasattr(row, "handling_unit") or not row.handling_unit:
			continue

		hu = get_handling_unit(row.handling_unit)

		if abs(hu.stock_qty - row.stock_qty) < frappe.get_precision(row.doctype, qty_field):
			frappe.throw(
				_(f"Row #{row.idx}: the Handling Unit for Item {row.item_code} has qty of {hu.stock_qty}.")
			)

	return doc
