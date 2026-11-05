# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
from frappe.model.create_new import make_new_doc as frappe_make_new_doc

import frappe

from beam.beam.mobile_access import ensure_document_access
from beam.beam.mobile_purchase_receipt import (
	map_with_ignore_permissions,
	purchase_receipt_from_route_id,
	receive_form_route_id,
)


@frappe.whitelist()
def make_new_doc(doctype, docname=None):
	if doctype == "Stock Entry":
		doc = frappe_make_new_doc(doctype)
		doc.purpose = "Material Transfer"
		return doc

	if doctype == "Purchase Receipt":
		doc = purchase_receipt_from_route_id(docname)
		return doc.as_dict()

	if doctype == "Delivery Note":
		ensure_document_access("Sales Order", docname, "read")
		doc = map_with_ignore_permissions(make_delivery_note, docname)
		return doc.as_dict()

	return None


@frappe.whitelist()
def resolve_receive_route(purchase_order: str) -> str:
	return receive_form_route_id(purchase_order)
