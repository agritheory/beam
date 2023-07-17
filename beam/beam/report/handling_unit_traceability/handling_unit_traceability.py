# Copyright (c) 2023, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe.query_builder import DocType


def execute(filters=None):
	if not any([filters.handling_unit, filters.delivery_note, filters.sales_invoice]):
		return

	if filters.handling_unit:
		stock_ledger_entry = DocType("Stock Ledger Entry")
		result = (
			frappe.qb.from_(stock_ledger_entry)
			.select(
				stock_ledger_entry.name,
				stock_ledger_entry.company,
				stock_ledger_entry.voucher_type,
				stock_ledger_entry.voucher_no,
				stock_ledger_entry.voucher_detail_no,
			)
			.where(stock_ledger_entry.handling_unit == filters.handling_unit)
		).run(as_dict=True)

	columns, data = [], []
	return columns, data
