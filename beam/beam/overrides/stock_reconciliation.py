from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import StockReconciliation


class BEAMStockReconciliation(StockReconciliation):
	def validate_inventory_dimension(self):
		pass

	# TODO: allow defeat of removal of items with no change
	# Do not make stock entries
