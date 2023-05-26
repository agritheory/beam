import frappe
import json
import datetime


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def handling_unit_query(doctype, txt, searchfield, start=0, page_len=20, filters=None):
	filters = frappe._dict({}) if not filters else filters
	return frappe.db.sql(
		"""
		SELECT
			`tabStock Ledger Entry`.handling_unit
		FROM `tabStock Ledger Entry`
		WHERE `tabStock Ledger Entry`.item_code = %(item_code)s
		AND `tabStock Ledger Entry`.warehouse = %(warehouse)s
		ORDER BY `tabStock Ledger Entry`.modified DESC
		LIMIT %(page_len)s, %(start)s
	""",
		{
			"item_code": filters.get("item_code"),
			"warehouse": filters.get("warehouse"),
			"start": start,
			"page_len": page_len,
		},
	)
