import frappe

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
	):
		return doc
	for row in doc.items:
		if not frappe.get_value("Item", row.item_code, "is_stock_item"):
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
