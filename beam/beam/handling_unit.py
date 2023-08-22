import frappe
from erpnext.stock.stock_ledger import NegativeStockError

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
			precision_denominator = 1 / pow(100, frappe.get_precision(row.doctype, "actual_qty"))
			hu = get_handling_unit(row.handling_unit)
			# transfer the entire handling unit's quantity
			if abs(hu.stock_qty - row.actual_qty) == 0.0 or (
				abs(hu.stock_qty - row.actual_qty) < precision_denominator
			):
				row.to_handling_unit = row.handling_unit
			else:  # transfer less than the entire handling unit's quantity, generate an new HU
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
				if abs(hu.stock_qty - row.get(qty_field)) != 0.0 and (
					hu.stock_qty - row.get(qty_field) < precision_denominator
				):
					error = True
			# outgoing
			elif row.get("t_warehouse") and not row.get("s_warehouse"):
				if abs(hu.stock_qty - row.get(qty_field)) != 0.0 and (
					hu.stock_qty - row.get(qty_field) > precision_denominator
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
