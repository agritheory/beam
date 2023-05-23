from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry

from beam.beam.overrides.handling_unit_mixin import (
	assign_handling_unit,
	patched_get_sl_entries,
	patched_make_sl_entries,
)


class CustomStockEntry(StockEntry):
	def on_submit(self):
		super().on_submit()

	def on_cancel(self):
		super().on_cancel()

	def before_submit(self):
		super().before_submit()

	def assign_handling_units(self):
		if self.purpose not in ("Material Receipt", "Manufacture", "Repack"):
			return
		for row in self.items:
			if any([row.is_finished_item, self.purpose == "Material Receipt", row.is_scrap_item]):
				assign_handling_unit(row)

	def make_sl_entries(self, sl_entries, allow_negative_stock=False, via_landed_cost_voucher=False):
		patched_make_sl_entries(sl_entries, allow_negative_stock, via_landed_cost_voucher)

	def get_sl_entries(self, d, args):
		return patched_get_sl_entries(self, d, args)
