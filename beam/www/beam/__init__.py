# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
from frappe.model.create_new import make_new_doc as frappe_make_new_doc


@frappe.whitelist()
def make_new_doc(doctype, docname=None):
	if doctype == "Stock Entry":
		doc = frappe_make_new_doc(doctype)
		doc.purpose = "Material Transfer"
		return doc
	elif doctype == "Purchase Receipt":
		return make_purchase_receipt(docname).as_dict()
	elif doctype == "Delivery Note":
		return make_delivery_note(docname).as_dict()


# @frappe.whitelist()
# def make_mapped_doc(doctype, docname):
# 	print(doctype, docname)
# 	if doctype in ['Purchase Order']:
# 		return
# 	elif doctype in ['Sales Order']:
# 		print('map sales order')
