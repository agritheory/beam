# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import re
from urllib.parse import urlparse, parse_qs

import frappe
import pytest

from playwright.sync_api import expect
from beam.tests.test_utils import use_current_db_transaction


# NOTE: any navigation tests should be done using `expect(page).to_have_url` since
# `page.expect_navigation()` won't work with Beam's hash-based routes


@pytest.mark.order(2)
def test_complete_partial_receipt(page):
	# navigate in the following order: Home -> Receive -> Purchase Order
	page.get_by_text("Receive").click()
	page.locator("css=.beam_list-item").first.click()

	# get the selected Purchase Order
	parsed_url = urlparse(page.url.replace("#", ""))
	order_id = parse_qs(parsed_url.query)["id"][0]
	assert order_id

	# find the first item in the list
	item = page.locator("css=.box .beam_list-item").first
	item_code, *others = item.inner_text().split("\n")
	item_count = page.locator("css=.box .beam_item-count").first
	expect(item_count).to_have_text(re.compile("0/"))

	assert item_code == "Cloudberry"

	frappe.db.rollback()
	frappe.db.begin()

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
		expect(item_count).to_have_text(re.compile("1/"))

	# ensure there are no existing Purchase Receipts against this Purchase Order
	receipt = frappe.db.exists(
		"Purchase Receipt Item",
		{"docstatus": 0, "purchase_order": order_id, "item_code": item_code},
	)
	#assert not receipt

	# check that a draft Purchase Receipt is created
	page.get_by_text("SAVE", exact=True).click()
	page.wait_for_timeout(1000)
	with use_current_db_transaction():
		receipts = frappe.get_all(
			"Purchase Receipt Item",
			filters={"purchase_order": order_id, "item_code": item_code},
			fields=["docstatus", "received_qty", "creation", "parent"],
			order_by="creation desc",
		)
	assert len(receipts) >= 1
	assert receipts[0]["docstatus"] == 0
	assert receipts[0]["received_qty"] == 1

	# check that the draft Purchase Receipt is submitted
	page.get_by_text("RECEIVE", exact=True).click()
	page.wait_for_timeout(1500)
	with use_current_db_transaction():
		receipts = frappe.get_all(
			"Purchase Receipt Item",
			filters={"purchase_order": order_id, "item_code": item_code},
			fields=["docstatus", "received_qty", "creation"],
			order_by="creation desc",
			limit=1
		)
	assert len(receipts) == 1
	assert receipts[0]["docstatus"] == 1
	assert receipts[0]["received_qty"] == 1
