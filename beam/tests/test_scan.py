import frappe
import pytest

"""
1. Test that a scanned item code in a list view returns the correct values for filtering
2. Test that a scanned item code in a list view returns the correct value for route change
3. Test that a scanned item code in a form view returns an object like `get_item_details`
4. Test that a scanned handling unit in a list view returns the correct value for route change
5. Test that a scanned handling unit in a form view returns an object like `get_item_details`
"""


def test_item_scan_from_list_view_for_filter():
	# purchase receipt listview
	item_barcode = frappe.get_value("Item Barcode", {"parent": "Butter"}, "barcode")
	scan = frappe.call(
		"beam.beam.scan.scan",
		**{"barcode": str(item_barcode), "context": {"listview": "Purchase Receipt"}, "current_qty": 1}
	)
	assert scan[0].get("action") == "filter"
	assert scan[0].get("doctype") == "Purchase Receipt Item"
	assert scan[0].get("field") == "item_code"
	assert scan[0].get("target") == "Butter"


def test_item_scan_from_list_view_for_route():
	# item listview
	item_barcode = frappe.get_value("Item Barcode", {"parent": "Butter"}, "barcode")
	scan = frappe.call(
		"beam.beam.scan.scan",
		**{"barcode": str(item_barcode), "context": {"listview": "Item"}, "current_qty": 1}
	)
	assert scan[0].get("action") == "route"
	assert scan[0].get("doctype") == "Item"
	assert scan[0].get("field") == "Item"
	assert scan[0].get("target") == "Butter"


def test_item_scan_from_form_view():
	context = {
		"frm": "Purchase Receipt",
		"doc": {
			"docstatus": 0,
			"doctype": "Purchase Receipt",
			"name": "new-purchase-receipt-1",
			"__islocal": 1,
			"__unsaved": 1,
			"owner": "Administrator",
			"naming_series": "MAT-PRE-.YYYY.-",
			"posting_date": "2023-06-21",
			"set_posting_time": 0,
			"company": "Ambrosia Pie Company",
			"apply_putaway_rule": 0,
			"is_return": 0,
			"currency": "USD",
			"buying_price_list": "Standard Buying",
			"price_list_currency": "USD",
			"ignore_pricing_rule": 0,
			"is_subcontracted": 0,
			"disable_rounded_total": 0,
			"apply_discount_on": "Grand Total",
			"status": "Draft",
			"group_same_items": 0,
			"is_internal_supplier": 0,
			"is_old_subcontracting_flow": 0,
			"items": [
				{
					"docstatus": 0,
					"doctype": "Purchase Receipt Item",
					"name": "new-purchase-receipt-item-1",
					"__islocal": 1,
					"__unsaved": 1,
					"owner": "Administrator",
					"has_item_scanned": 0,
					"received_qty": 0,
					"stock_uom": "Nos",
					"retain_sample": 0,
					"margin_type": "",
					"is_free_item": 0,
					"is_fixed_asset": 0,
					"allow_zero_valuation_rate": 0,
					"include_exploded_items": 0,
					"cost_center": "Main - APC",
					"page_break": 0,
					"parent": "new-purchase-receipt-1",
					"parentfield": "items",
					"parenttype": "Purchase Receipt",
					"idx": 1,
					"qty": 0,
					"rejected_qty": 0,
					"conversion_factor": 0,
					"received_stock_qty": 0,
					"stock_qty": 0,
					"returned_qty": 0,
					"price_list_rate": 0,
					"base_price_list_rate": 0,
					"margin_rate_or_amount": 0,
					"rate_with_margin": 0,
					"discount_amount": 0,
					"base_rate_with_margin": 0,
					"rate": 0,
					"amount": 0,
					"base_rate": 0,
					"base_amount": 0,
					"stock_uom_rate": 0,
					"net_rate": 0,
					"net_amount": 0,
					"base_net_rate": 0,
					"base_net_amount": 0,
					"valuation_rate": 0,
					"item_tax_amount": 0,
					"rm_supp_cost": 0,
					"landed_cost_voucher_amount": 0,
					"rate_difference_with_purchase_invoice": 0,
					"billed_amt": 0,
					"weight_per_unit": 0,
					"total_weight": 0,
				}
			],
			"posting_time": "03:51:13",
			"conversion_rate": 1,
			"plc_conversion_rate": 1,
			"taxes_and_charges": "US ST 6% - APC",
			"taxes": [
				{
					"docstatus": 0,
					"doctype": "Purchase Taxes and Charges",
					"name": "new-purchase-taxes-and-charges-1",
					"__islocal": 1,
					"__unsaved": 1,
					"owner": "Administrator",
					"category": "Total",
					"add_deduct_tax": "Add",
					"charge_type": "On Net Total",
					"included_in_print_rate": 0,
					"included_in_paid_amount": 0,
					"cost_center": "Main - APC",
					"account_currency": None,
					"parent": "new-purchase-receipt-1",
					"parentfield": "taxes",
					"parenttype": "Purchase Receipt",
					"idx": 1,
					"row_id": None,
					"account_head": "ST 6% - APC",
					"description": "ST 6% @ 6.0",
					"rate": 6,
					"tax_amount": 0,
					"tax_amount_after_discount_amount": 0,
					"total": 0,
					"base_tax_amount": 0,
					"base_total": 0,
					"base_tax_amount_after_discount_amount": 0,
					"item_wise_tax_detail": '{"undefined":[6,0]}',
				}
			],
			"base_net_total": 0,
			"net_total": 0,
			"base_total": 0,
			"total": 0,
			"total_qty": 0,
			"rounding_adjustment": 0,
			"grand_total": 0,
			"taxes_and_charges_deducted": 0,
			"taxes_and_charges_added": 0,
			"base_grand_total": 0,
			"base_taxes_and_charges_added": 0,
			"base_taxes_and_charges_deducted": 0,
			"total_taxes_and_charges": 0,
			"base_total_taxes_and_charges": 0,
			"base_rounding_adjustment": 0,
			"rounded_total": 0,
			"base_rounded_total": 0,
			"in_words": "",
			"base_in_words": "",
			"base_discount_amount": 0,
		},
	}
	item_barcode = frappe.get_value("Item Barcode", {"parent": "Butter"}, "barcode")
	scan = frappe.call(
		"beam.beam.scan.scan", **{"barcode": str(item_barcode), "context": context, "current_qty": 1}
	)
	assert scan[0].get("action") == "add_or_increment"
	assert scan[0].get("doctype") == "Purchase Receipt Item"
	assert scan[0].get("field") == "item_code"
	assert scan[0].get("target") == "Butter"
	# TODO: add assertions that show harmonization with get_item_details
