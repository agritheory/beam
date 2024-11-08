# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe.model.create_new import make_new_doc as frappe_make_new_doc
from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt


@frappe.whitelist()
def make_new_doc(doctype, docname=None):
	print(doctype, docname)
	if doctype == "Stock Entry":
		doc = frappe_make_new_doc(doctype)
		doc.purpose = "Material Transfer"
	elif doctype == "Purchase Receipt":
		doc = make_purchase_receipt(docname).as_dict()
	return doc


# @frappe.whitelist()
# def make_mapped_doc(doctype, docname):
# 	print(doctype, docname)
# 	if doctype in ['Purchase Order']:
# 		return
# 	elif doctype in ['Sales Order']:
# 		print('map sales order')
