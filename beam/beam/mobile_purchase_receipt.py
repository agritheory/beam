# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

"""Purchase Receipt loading for BEAM mobile (PO or saved PR in the URL)."""

from __future__ import annotations

import frappe
from frappe import _
from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt
from frappe.model.document import Document

from beam.beam.mobile_access import ensure_document_access


def map_with_ignore_permissions(map_fn, source_name):
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


def draft_purchase_receipt_for_order(purchase_order: str) -> str | None:
	row = frappe.db.sql(
		"""
		select pr.name
		from `tabPurchase Receipt` pr
		inner join `tabPurchase Receipt Item` pri on pri.parent = pr.name
		where pri.purchase_order = %s and pr.docstatus = 0
		order by pr.modified desc
		limit 1
		""",
		purchase_order,
	)
	return row[0][0] if row else None


def receive_form_route_id(purchase_order: str) -> str:
	return draft_purchase_receipt_for_order(purchase_order) or purchase_order


def purchase_receipt_from_route_id(route_id: str):
	if frappe.db.exists("Purchase Receipt", route_id):
		ensure_document_access("Purchase Receipt", route_id, "read")
		return frappe.get_doc("Purchase Receipt", route_id)

	if not frappe.db.exists("Purchase Order", route_id):
		frappe.throw(_("Purchase Order {0} not found").format(route_id))

	draft_name = draft_purchase_receipt_for_order(route_id)
	if draft_name:
		ensure_document_access("Purchase Receipt", draft_name, "read")
		return frappe.get_doc("Purchase Receipt", draft_name)

	ensure_document_access("Purchase Order", route_id, "read")
	return map_with_ignore_permissions(make_purchase_receipt, route_id)
