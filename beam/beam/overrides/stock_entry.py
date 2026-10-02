# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry
from frappe.utils import cstr, flt

from beam.beam.doctype.beam_settings.beam_settings import create_beam_settings
from beam.beam.handling_unit import is_scrap_item


class BEAMStockEntry(StockEntry):
	def update_stock_ledger(self):
		settings = (
			create_beam_settings(self.company)
			if not frappe.db.exists("BEAM Settings", {"company": self.company})
			else frappe.get_doc("BEAM Settings", {"company": self.company})
		)
		sl_entries = []
		finished_item_row = self.get_finished_item_row()
		self.get_sle_for_source_warehouse(sl_entries, finished_item_row)
		self.get_sle_for_target_warehouse(sl_entries, finished_item_row)

		# Ensure handling_unit is set on SLE entries if enabled
		if settings.enable_handling_units:
			for sle in sl_entries:
				if hasattr(sle, "get") and "voucher_detail_no" in sle:
					item_row = next(
						(item for item in self.items if item.name == sle.get("voucher_detail_no")), None
					)
					if item_row:
						# For source warehouse (consumption), use handling_unit
						if (
							sle.get("warehouse") == item_row.s_warehouse
							and hasattr(item_row, "handling_unit")
							and item_row.handling_unit
						):
							sle["handling_unit"] = item_row.handling_unit
						# For target warehouse (receipt), use to_handling_unit if it exists, otherwise handling_unit
						elif sle.get("warehouse") == item_row.t_warehouse:
							if hasattr(item_row, "to_handling_unit") and item_row.to_handling_unit:
								sle["handling_unit"] = item_row.to_handling_unit
							elif hasattr(item_row, "handling_unit") and item_row.handling_unit:
								sle["handling_unit"] = item_row.handling_unit

		if self.docstatus == 2:
			sl_entries.reverse()
		self.make_sl_entries(sl_entries)

		if self.docstatus == 2 and settings.enable_handling_units:
			hu_sles = self.make_handling_unit_sles()
			self.make_sl_entries(hu_sles)

	def make_handling_unit_sles(self):
		hu_sles = []
		for d in self.get("items"):
			# Only process when cancelling AND user wants to keep separate (NOT recombine)
			if self.docstatus != 2 or d.recombine_on_cancel or not d.handling_unit:
				continue

			if d.handling_unit and d.to_handling_unit:
				# Material Transfer types: both HUs on the same row
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
			elif d.s_warehouse and not d.t_warehouse:
				# Repack/Manufacture source row: re-consume from source HU
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
			elif d.t_warehouse and not d.s_warehouse:
				# Repack/Manufacture target row: re-add to target HU
				sle = self.get_sl_entries(
					d,
					{
						"warehouse": cstr(d.t_warehouse),
						"actual_qty": flt(d.transfer_qty),
						"incoming_rate": flt(d.valuation_rate),
					},
				)
				sle["handling_unit"] = d.handling_unit
				sle["is_cancelled"] = 0
				hu_sles.append(sle)
		return hu_sles


@frappe.whitelist()
def set_rows_to_recombine(docname: str, to_recombine=None) -> None:
	doc = frappe.get_doc("Stock Entry", docname)
	settings = (
		create_beam_settings(doc.company)
		if not frappe.db.exists("BEAM Settings", {"company": doc.company})
		else frappe.get_doc("BEAM Settings", {"company": doc.company})
	)
	if not settings.enable_handling_units:
		return
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


# This function validates stock entry items to prevent missing handling units.
def validate_items_with_handling_unit(doc, method=None):
	beam_settings = frappe.get_doc("BEAM Settings", doc.company)
	if not beam_settings.enable_handling_units:
		return

	if frappe.flags.get("beam_allow_source_rows_without_hu"):
		return

	if doc.stock_entry_type != "Material Receipt":
		for row in doc.items:
			if not frappe.get_value("Item", row.item_code, "enable_handling_unit"):
				continue
			elif is_scrap_item(row) and not frappe.get_value(
				"BOM Scrap Item",
				{"item_code": row.item_code, "parent": doc.get("bom_no")},
				"create_handling_unit",
			):
				continue
			elif (
				doc.stock_entry_type in ("Repack", "Manufacture")
				and not (row.t_warehouse or row.is_finished_item or is_scrap_item(row))
				and not row.handling_unit
			):
				frappe.throw(frappe._(f"Row #{row.idx}: Handling Unit is missing for item {row.item_code}"))
			elif row.handling_unit:
				continue
			elif not row.handling_unit:
				frappe.throw(frappe._(f"Row #{row.idx}: Handling Unit is missing for item {row.item_code}"))
