# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

# To test locally:
#  active the virtual environment
#  bench start, and then run:
#  pytest ./beam/tests/mobile/test_manufacture.py --browser firefox --headed --disable-warnings

import re

import frappe
import pytest
from playwright.sync_api import expect

from beam.tests.playwright_utils import use_current_db_transaction


@pytest.mark.order(1)
def test_complete_partial_stock_entry(page):
	"""
	This test needs to disable handling units on Beam Settings and
	populate the item in Stock Entry, otherwise we will obtain the error:

	'frappe.exceptions.ValidationError: Row #1: Handling Unit is missing for item Butter'
	  or
	'erpnext.stock.stock_ledger.NegativeStockError: 1.0 units of
	Item Butter needed in Warehouse Refrigerator - APC to complete this transaction.'
	"""

	frappe.db.set_value("BEAM Settings", "Ambrosia Pie Company", "enable_handling_units", 0)
	frappe.db.commit()

	butter = frappe.new_doc("Stock Entry")
	butter.stock_entry_type = butter.purpose = "Material Receipt"
	butter.append(
		"items",
		{
			"item_code": "Butter",
			"qty": 5,  # intentionally to help with demand tests
			"t_warehouse": "Refrigerator - APC",
			"uom": "Pound",
			"basic_rate": 4.50,
			"expense_account": "5119 - Stock Adjustment - APC",
		},
	)

	butter.save()
	butter.submit()
	frappe.db.commit()

	# navigate in the following order: Home -> Manufacture -> Work Order
	page.get_by_text("Manufacture").click()

	expect(page.locator("css=.beam_list-item").first).to_be_visible()
	page.locator("css=.beam_list-item").first.click()

	# get the selected Work Order
	order_id = page.url.split("/")[-1]
	assert order_id

	expect(page.locator("css=.box .beam_list-item").first).to_be_visible()
	# ensure there are no existing Stock Entries against this Work Order
	entry = frappe.db.exists(
		"Stock Entry",
		{"docstatus": 0, "work_order": order_id},
	)
	assert not entry

	# find the first item in the list
	item = page.locator("css=.box .beam_list-item").first
	expect(item).to_be_visible(timeout=15000)
	item_code, *others = item.inner_text().split("\n")
	item_count = page.locator("css=.box .beam_item-count").first
	expect(item_count).to_have_text(re.compile("0/"), timeout=15000)

	assert item_code == "Butter"

	# ensure that the item has barcodes
	barcodes = frappe.get_all(
		"Item Barcode", filters={"parenttype": "Item", "parent": item_code}, pluck="barcode"
	)
	assert len(barcodes) > 0

	# scan barcode and expect increment by 1
	with page.expect_request(
		lambda request: request.headers.get("x-frappe-cmd") == "beam.beam.scan.scan"
	):
		page.evaluate("barcode => scanner.simulate(window, barcode)", barcodes[0])
		expect(item_count).to_have_text(re.compile("1/"), timeout=15000)

	# check that a draft Stock Entry is created
	page.get_by_text("SAVE", exact=True).click()
	page.wait_for_timeout(1000)
	with use_current_db_transaction():
		entries = frappe.get_all(
			"Stock Entry",
			filters={"work_order": order_id},
			fields=["docstatus"],
		)
	assert len(entries) >= 1
	assert entries[0]["docstatus"] == 0

	# check that the draft Purchase Receipt is submitted
	page.get_by_text("TRANSFER", exact=True).click()
	page.wait_for_timeout(1000)
	with use_current_db_transaction():
		receipts = frappe.get_all(
			"Stock Entry",
			filters={"work_order": order_id},
			fields=["docstatus"],
		)
	assert len(receipts) >= 1
	assert receipts[0]["docstatus"] == 1

	frappe.db.set_value("BEAM Settings", "Ambrosia Pie Company", "enable_handling_units", 1)
	frappe.db.commit()
