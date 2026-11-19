# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

"""Purchase Receipt: receive failed gate inspections into rejected warehouse."""

from __future__ import annotations

import frappe
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import PurchaseReceipt
from frappe import _
from frappe.utils import flt


def resolve_rejected_warehouse(doc: frappe.Document, item: frappe.Document) -> str | None:
	if item.get("rejected_warehouse"):
		return item.rejected_warehouse
	if doc.get("rejected_warehouse"):
		return doc.rejected_warehouse
	rows = frappe.get_all(
		"Warehouse",
		filters={"company": doc.company, "is_rejected_warehouse": 1, "disabled": 0},
		pluck="name",
		limit=1,
	)
	return rows[0] if rows else None


def apply_rejected_inspection_from_qi(doc: frappe.Document, method=None) -> None:
	"""On submit, move qty to rejected_warehouse when linked QI was rejected."""
	if doc.doctype != "Purchase Receipt" or doc.docstatus != 1:
		return

	for item in doc.get("items") or []:
		if not item.get("quality_inspection"):
			continue
		qi_status = frappe.db.get_value("Quality Inspection", item.quality_inspection, "status")
		if qi_status != "Rejected":
			continue

		received = flt(item.received_qty) or (flt(item.qty) + flt(item.rejected_qty))
		if received <= 0:
			continue

		rejected_warehouse = resolve_rejected_warehouse(doc, item)
		if not rejected_warehouse:
			frappe.throw(
				_(
					"Row #{0}: Set a rejected warehouse on the receipt (or company rejected warehouse) "
					"to receive material that failed quality inspection."
				).format(item.idx),
				title=_("Rejected Warehouse Required"),
			)

		item.rejected_qty = received
		item.qty = 0
		item.received_qty = received
		item.rejected_warehouse = rejected_warehouse


class BEAMPurchaseReceipt(PurchaseReceipt):
	def validate_qi_rejection(self, row):
		"""Allow submit when failed inspection is booked as rejected stock (ERPNext rejected_qty)."""
		if flt(row.rejected_qty) > 0 and row.rejected_warehouse:
			return
		super().validate_qi_rejection(row)
