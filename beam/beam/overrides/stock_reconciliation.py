# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import StockReconciliation


class BEAMStockReconciliation(StockReconciliation):
	pass


@frappe.whitelist()
def get_items(
	warehouse, posting_date, posting_time, company, item_code=None, ignore_empty_stock=False
):
	from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import (
		get_items as erpnext_get_items,
	)
	from erpnext.stock.doctype.item.item import get_item_defaults
	from erpnext.stock.doctype.inventory_dimension.inventory_dimension import get_inventory_dimensions

	items = erpnext_get_items(
		warehouse, posting_date, posting_time, company, item_code, ignore_empty_stock
	)
	dimensions = get_inventory_dimensions()

	filtered_items = []
	
	for item in items:
		if item.get("valuation_rate", 0) == 0:
			continue

		item_defaults = get_item_defaults(item["item_code"], company)
		item["stock_uom"] = item_defaults.get("stock_uom")

		for dim in dimensions:
			fieldname = dim.get("fieldname")
			if fieldname and fieldname in item_defaults:
				item[fieldname] = item_defaults[fieldname]
		
		filtered_items.append(item)
	
	return filtered_items
