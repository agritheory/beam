import copy

import frappe
from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry
from erpnext.stock.doctype.stock_entry_detail.stock_entry_detail import StockEntryDetail
from frappe.utils import cstr, flt
from typing_extensions import Self


class BEAMStockEntry(StockEntry):
	def update_stock_ledger(self):
		sl_entries = []
		finished_item_row = self.get_finished_item_row()
		self.get_sle_for_source_warehouse(sl_entries, finished_item_row)
		self.get_sle_for_target_warehouse(sl_entries, finished_item_row)
		if self.docstatus == 2:
			sl_entries.reverse()
		self.make_sl_entries(sl_entries)

		if self.docstatus == 2:
			hu_sles = self.make_handling_unit_sles()
			self.make_sl_entries(hu_sles)

	def make_handling_unit_sles(self):
		hu_sles = []
		for d in self.get("items"):
			if self.docstatus == 2 and not d.recombine_on_cancel and d.handling_unit and d.to_handling_unit:
				sle = self.get_sl_entries(
					d,
					{
						"warehouse": cstr(d.s_warehouse),
						"actual_qty": -flt(d.transfer_qty),
						"incoming_rate": flt(d.valuation_rate),
					},
				)
				sle["handling_unit"] = d.handling_unit
				sle["is_cancelled"] = 0
				hu_sles.append(sle)
				_sle = self.get_sl_entries(
					d,
					{
						"warehouse": cstr(d.t_warehouse),
						"actual_qty": flt(d.transfer_qty),
						"incoming_rate": flt(d.valuation_rate),
					},
				)
				_sle["handling_unit"] = d.to_handling_unit
				_sle["is_cancelled"] = 0
				hu_sles.append(_sle)
		return hu_sles


@frappe.whitelist()
def set_rows_to_recombine(docname: str, to_recombine=None) -> None:
	doc = frappe.get_doc("Stock Entry", docname)
	if not to_recombine:
		return
	for row in doc.items:
		if row.name in to_recombine:
			row.db_set("recombine_on_cancel", True)
	return


@frappe.whitelist()
@frappe.read_only()
def get_handling_units_for_item_code(doctype, txt, searchfield, start, page_len, filters):
	StockLedgerEntry = frappe.qb.DocType("Stock Ledger Entry")
	return (
		frappe.qb.from_(StockLedgerEntry)
		.select(StockLedgerEntry.handling_unit)
		.where(
			(StockLedgerEntry.item_code == filters.get("item_code"))
			& (StockLedgerEntry.handling_unit != "")
		)
		.orderby(StockLedgerEntry.posting_date, order=frappe.qb.desc)
		.groupby(StockLedgerEntry.handling_unit)
		.run(as_dict=False)
	)


@frappe.whitelist()
@frappe.read_only()
def get_handling_unit_qty(voucher_no, handling_unit, warehouse):
	return frappe.db.get_value(
		"Stock Ledger Entry",
		{
			"voucher_no": voucher_no,
			"handling_unit": handling_unit,
			"warehouse": warehouse,
		},
		["qty_after_transaction"],
	)
