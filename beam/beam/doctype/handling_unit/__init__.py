import frappe
from pypika import Order


@frappe.whitelist()
@frappe.read_only()
@frappe.validate_and_sanitize_search_inputs
def handling_unit_query(doctype, txt, searchfield, start=0, page_len=20, filters=None):
	filters = frappe._dict({}) if not filters else filters
	stock_ledger_entry = frappe.qb.DocType("Stock Ledger Entry")
	return (
		frappe.qb.from_(stock_ledger_entry)
		.select(stock_ledger_entry.handling_unit)
		.where(stock_ledger_entry.item_code == filters.get("item_code"))
		.where(stock_ledger_entry.warehouse == filters.get("warehouse"))
		.orderby("modified", order=Order.desc)
		.limit(page_len)
		.offset(start)
	).run()
