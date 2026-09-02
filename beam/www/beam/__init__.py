# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
from frappe.model.create_new import make_new_doc as frappe_make_new_doc
from frappe.model.document import Document


def map_with_ignore_permissions(map_fn, source_name):
	"""ERPNext mapping calls Address.render_address during set_missing_values.

	Warehouse/mobile users often lack Address read. Document.has_permission only
	honors the document's own flags.ignore_permissions (not frappe.flags), and
	BuyingController passes that flag into get_party_details. Set it on the
	target before set_missing_values runs.
	"""
	original_run_method = Document.run_method

	def run_method(self, method, *args, **kwargs):
		if method == "set_missing_values":
			self.flags.ignore_permissions = True
		return original_run_method(self, method, *args, **kwargs)

	Document.run_method = run_method
	try:
		return map_fn(source_name)
	finally:
		Document.run_method = original_run_method


@frappe.whitelist()
def make_new_doc(doctype, docname=None):
	if doctype == "Stock Entry":
		doc = frappe_make_new_doc(doctype)
		doc.purpose = "Material Transfer"
		return doc

	if doctype == "Purchase Receipt":
		frappe.has_permission("Purchase Order", "read", doc=docname, throw=True)
		doc = map_with_ignore_permissions(make_purchase_receipt, docname)
		return doc.as_dict()

	if doctype == "Delivery Note":
		frappe.has_permission("Sales Order", "read", doc=docname, throw=True)
		doc = map_with_ignore_permissions(make_delivery_note, docname)
		return doc.as_dict()

	return None
