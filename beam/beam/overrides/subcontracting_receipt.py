# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from erpnext.subcontracting.doctype.subcontracting_receipt.subcontracting_receipt import (
	SubcontractingReceipt,
)
from frappe.utils import cint, cstr, flt


class BEAMSubcontractingReceipt(SubcontractingReceipt):
	def update_stock_ledger(self, allow_negative_stock=False, via_landed_cost_voucher=False):
		self.update_ordered_and_reserved_qty()

		sl_entries = []
		stock_items = self.get_stock_items()

		for item in self.get("items"):
			if item.item_code in stock_items and item.warehouse:
				scr_qty = flt(item.qty) * flt(item.conversion_factor)

				if scr_qty:
					sle = self.get_sl_entries(
						item, {"actual_qty": flt(scr_qty), "serial_no": cstr(item.serial_no).strip()}
					)
					rate_db_precision = 6 if cint(self.precision("rate", item)) <= 6 else 9
					incoming_rate = flt(item.rate, rate_db_precision)
					sle.update(
						{"incoming_rate": incoming_rate, "recalculate_rate": 1, "handling_unit": item.handling_unit}
					)
					sl_entries.append(sle)

				if flt(item.rejected_qty) != 0:
					sl_entries.append(
						self.get_sl_entries(
							item,
							{
								"warehouse": item.rejected_warehouse,
								"actual_qty": flt(item.rejected_qty) * flt(item.conversion_factor),
								"serial_no": cstr(item.rejected_serial_no).strip(),
								"incoming_rate": 0.0,
								"handling_unit": item.handling_unit,
							},
						)
					)

		make_sl_entries_for_supplier_warehouse(self, sl_entries)
		self.make_sl_entries(
			sl_entries,
			allow_negative_stock=allow_negative_stock,
			via_landed_cost_voucher=via_landed_cost_voucher,
		)


def make_sl_entries_for_supplier_warehouse(self, sl_entries):
	if hasattr(self, "supplied_items"):
		sle_hu = get_sle(self)
		for item in self.get("supplied_items"):
			# negative quantity is passed, as raw material qty has to be decreased
			# when SCR is submitted and it has to be increased when SCR is cancelled
			handling_unit = get_handling_unit_for_consumption(sle_hu, item)
			sl_entries.append(
				self.get_sl_entries(
					item,
					{
						"item_code": item.rm_item_code,
						"warehouse": self.supplier_warehouse,
						"actual_qty": -1 * flt(item.consumed_qty, item.precision("consumed_qty")),
						"dependant_sle_voucher_detail_no": item.reference_name,
						"handling_unit": handling_unit,
					},
				)
			)


def get_handling_unit_for_consumption(sle_hu, item):
	if sle_hu.get(item.subcontracting_order):
		for row in sle_hu.get(item.subcontracting_order):
			if row.item_code == item.rm_item_code:
				return row.handling_unit


def get_sle(self):
	sle_hu_map = {}
	for row in self.items:
		if row.subcontracting_order:
			if stock_entry := frappe.db.exists(
				"Stock Entry", {"subcontracting_order": row.subcontracting_order, "docstatus": 1}
			):
				sle_hu_map[row.subcontracting_order] = frappe.get_all(
					"Stock Ledger Entry",
					filters={
						"voucher_type": "Stock Entry",
						"voucher_no": stock_entry,
						"warehouse": self.supplier_warehouse,
					},
					fields=["name", "handling_unit", "item_code"],
				)
	return sle_hu_map
