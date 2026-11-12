# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

"""Purchase Receipt loading for BEAM mobile (PO or saved PR in the URL)."""

from __future__ import annotations

import frappe
from frappe import _
from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt
from frappe.model.document import Document

from beam.beam.mobile_access import ensure_document_access


def map_with_ignore_permissions(map_fn, source_name, **kwargs):
	original_run_method = Document.run_method

	def run_method(self, method, *args, **kwargs):
		if method == "set_missing_values":
			self.flags.ignore_permissions = True
		return original_run_method(self, method, *args, **kwargs)

	Document.run_method = run_method
	try:
		return map_fn(source_name, **kwargs)
	finally:
		Document.run_method = original_run_method


def append_pending_order_lines(purchase_receipt: Document) -> Document:
	"""Add Purchase Order lines missing from a draft receipt, so they can still be received.
	Mobile saves only lines with a received qty, so a partial receipt drops the rest.
	"""
	if purchase_receipt.docstatus != 0:
		return purchase_receipt

	mapped_order_items = {row.purchase_order_item for row in purchase_receipt.items if row.purchase_order_item}
	purchase_orders = sorted({row.purchase_order for row in purchase_receipt.items if row.purchase_order})

	if not purchase_orders:
		return purchase_receipt

	# Lines already in another draft receipt are received there; offering them here too would double count.
	in_other_drafts = set(
		frappe.get_all(
			"Purchase Receipt Item",
			filters={
				"purchase_order": ["in", purchase_orders],
				"parent": ["!=", purchase_receipt.name],
				"docstatus": 0,
			},
			pluck="purchase_order_item",
		)
	)
	excluded = mapped_order_items | in_other_drafts

	for purchase_order in purchase_orders:
		filters = {"parent": purchase_order}
		if excluded:
			filters["name"] = ["not in", list(excluded)]
		missing = frappe.get_all("Purchase Order Item", filters=filters, pluck="name")
		if not missing:
			continue

		existing_rows = len(purchase_receipt.items)
		map_with_ignore_permissions(
			make_purchase_receipt,
			purchase_order,
			target_doc=purchase_receipt,
			args={"filtered_children": missing},
		)
		for row in purchase_receipt.items[existing_rows:]:
			row.received_qty = 0

	# Keep the Purchase Order line order, so appended lines don't end up after the counted ones.
	order_lines = frappe.get_all(
		"Purchase Order Item",
		filters={"parent": ["in", purchase_orders]},
		fields=["name", "parent", "idx"],
	)
	order_line_idx = {row.name: (row.parent, row.idx) for row in order_lines}
	purchase_receipt.items.sort(
		key=lambda row: order_line_idx.get(row.purchase_order_item, ("", row.idx or 0))
	)
	for idx, row in enumerate(purchase_receipt.items, start=1):
		row.idx = idx

	return purchase_receipt


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
		return append_pending_order_lines(frappe.get_doc("Purchase Receipt", route_id))

	if not frappe.db.exists("Purchase Order", route_id):
		frappe.throw(_("Purchase Order {0} not found").format(route_id))

	draft_name = draft_purchase_receipt_for_order(route_id)
	if draft_name:
		ensure_document_access("Purchase Receipt", draft_name, "read")
		return append_pending_order_lines(frappe.get_doc("Purchase Receipt", draft_name))

	ensure_document_access("Purchase Order", route_id, "read")
	return map_with_ignore_permissions(make_purchase_receipt, route_id)
