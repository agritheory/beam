# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

# To test locally:
#  active the virtual environment
#  bench start, and then run:
#  pytest ./beam/tests/mobile/test_receive.py --browser firefox --headed --disable-warnings

import re
from urllib.parse import urlparse

import frappe
import pytest
from playwright.sync_api import expect

from beam.tests.test_utils import use_current_db_transaction

# NOTE: any navigation tests should be done using `expect(page).to_have_url` since
# `page.expect_navigation()` won't work with Beam's hash-based routes


@pytest.mark.order(2)
def test_scan_invalid_barcode(page):
	# navigate to a Purchase Order
	page.get_by_text("Receive").click()
	page.locator("css=.beam_list-item").first.click()

	# get the selected Purchase Order
	parsed_url = urlparse(page.url.replace("#", ""))
	path_parts = [p for p in parsed_url.path.split("/") if p]
	order_id = path_parts[-1] if path_parts else None
	assert order_id

	# find all items in the list
	all_item_counts = page.locator("css=.box .beam_item-count")

	# get all item counts before scanning invalid barcode
	initial_counts = []
	for i in range(all_item_counts.count()):
		count_text = all_item_counts.nth(i).inner_text()
		initial_counts.append(count_text)

	# ensure all items start with 0 count
	for count in initial_counts:
		assert count.startswith("0/"), f"Expected item to start with 0/, but got: {count}"

	# verify there are no existing Purchase Receipts created by test user
	with use_current_db_transaction():
		existing_receipts = frappe.get_all(
			"Purchase Receipt", filters={"owner": "support@agritheory.dev", "docstatus": 0}, fields=["name"]
		)
		assert (
			len(existing_receipts) == 0
		), f"Found existing draft Purchase Receipts created by test user: {existing_receipts}"

	# scan an invalid barcode that doesn't exist
	invalid_barcode = "INVALID_BARCODE_12345"
	page.evaluate("barcode => scanner.simulate(window, barcode)", invalid_barcode)

	page.wait_for_timeout(500)

	# verify ALL item counts remain unchanged (all should still start with "0/")
	initial_counts = []
	for i in range(all_item_counts.count()):
		count_text = all_item_counts.nth(i).inner_text()
		initial_counts.append(count_text)

	# ensure all items start with 0 count
	for count in initial_counts:
		assert count.startswith("0/"), f"Expected item to start with 0/, but got: {count}"

	# verify no draft Purchase Receipt was created by test user
	with use_current_db_transaction():
		new_receipts = frappe.get_all(
			"Purchase Receipt", filters={"owner": "support@agritheory.dev", "docstatus": 0}, fields=["name"]
		)
		assert (
			len(new_receipts) == 0
		), f"Invalid barcode scan should not create any Purchase Receipts, but found: {new_receipts}"


@pytest.mark.order(3)
def test_receive_without_scanning(page):
	"""Test trying to receive without scanning any items"""
	# navigate to a Purchase Order
	page.get_by_text("Receive").click()
	page.locator("css=.beam_list-item").first.click()

	# get the selected Purchase Order
	parsed_url = urlparse(page.url.replace("#", ""))
	path_parts = [p for p in parsed_url.path.split("/") if p]
	order_id = path_parts[-1] if path_parts else None
	assert order_id

	item = page.locator("css=.box .beam_list-item").first
	item_code, *others = item.inner_text().split("\n")

	# find all items in the list
	all_item_counts = page.locator("css=.box .beam_item-count")
	initial_counts = []
	for i in range(all_item_counts.count()):
		count_text = all_item_counts.nth(i).inner_text()
		initial_counts.append(count_text)

	# ensure all items start with 0 count
	for count in initial_counts:
		assert count.startswith("0/"), f"Expected item to start with 0/, but got: {count}"

	# count existing Purchase Receipts before attempting to save
	with use_current_db_transaction():
		existing_receipts = frappe.get_all(
			"Purchase Receipt Item",
			filters={"purchase_order": order_id, "item_code": item_code, "owner": "support@agritheory.dev"},
			fields=["docstatus", "received_qty"],
		)
		initial_count = len(existing_receipts)

	# try to click SAVE without scanning anything
	save_button = page.get_by_text("SAVE", exact=True)
	save_button.click()
	page.wait_for_timeout(1000)

	# verify no new draft Purchase Receipt was created
	with use_current_db_transaction():
		new_receipts = frappe.get_all(
			"Purchase Receipt Item",
			filters={"purchase_order": order_id, "item_code": item_code, "owner": "support@agritheory.dev"},
			fields=["docstatus", "received_qty"],
		)
		final_count = len(new_receipts)
		assert (
			final_count == initial_count
		), f"Expected no new receipts, but count changed from {initial_count} to {final_count}"


@pytest.mark.order(4)
def test_complete_partial_receipt(page):
	# navigate in the following order: Home -> Receive -> Purchase Order
	page.get_by_text("Receive").click()
	page.locator("css=.beam_list-item").first.click()

	# get the selected Purchase Order
	# NOTE: URL format changed: the id lives in the path after the hash (e.g. #/purchase-receipt/PUR-ORD-...)
	# this PR changed the URL format:
	# https://github.com/agritheory/beam/pull/274
	parsed_url = urlparse(page.url.replace("#", ""))
	path_parts = [p for p in parsed_url.path.split("/") if p]
	order_id = path_parts[-1] if path_parts else None

	assert order_id

	# find the first item in the list
	item = page.locator("css=.box .beam_list-item").first
	item_code, *others = item.inner_text().split("\n")
	item_count = page.locator("css=.box .beam_item-count").first
	expect(item_count).to_have_text(re.compile("0/"))

	assert item_code == "Cloudberry"

	# Refresh transaction to see setup data
	with use_current_db_transaction():
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
		{
			"docstatus": 0,
			"purchase_order": order_id,
			"item_code": item_code,
			"owner": "support@agritheory.dev",
		},
	)
	assert not receipt

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
			limit=1,
		)
	assert len(receipts) == 1
	assert receipts[0]["docstatus"] == 1
	assert receipts[0]["received_qty"] == 1


@pytest.mark.order(5)
def test_rapid_barcode_scanning(page):
	"""Test scanning multiple barcodes quickly"""
	# navigate to a Purchase Order
	page.get_by_text("Receive").click()
	page.locator("css=.beam_list-item").first.click()

	# get the selected Purchase Order
	parsed_url = urlparse(page.url.replace("#", ""))
	path_parts = [p for p in parsed_url.path.split("/") if p]
	order_id = path_parts[-1] if path_parts else None
	assert order_id

	# find the first item in the list
	item = page.locator("css=.box .beam_list-item").first
	item_code, *others = item.inner_text().split("\n")
	item_count = page.locator("css=.box .beam_item-count").first
	expect(item_count).to_have_text(re.compile("0/"))

	# get barcode for the item
	with use_current_db_transaction():
		barcodes = frappe.get_all(
			"Item Barcode", filters={"parenttype": "Item", "parent": item_code}, pluck="barcode"
		)
		assert len(barcodes) > 0

	# scan the same barcode multiple times quickly
	scan_count = 10
	for _ in range(scan_count):
		page.evaluate("barcode => scanner.simulate(window, barcode)", barcodes[0])
		# very short delay between scans to simulate rapid scanning
		page.wait_for_timeout(100)

	page.wait_for_timeout(1000)

	expect(item_count).to_have_text(re.compile(f"{scan_count}/"))

	page.get_by_text("SAVE", exact=True).click()
	page.wait_for_timeout(1000)

	with use_current_db_transaction():
		receipts = frappe.get_all(
			"Purchase Receipt Item",
			filters={"purchase_order": order_id, "item_code": item_code},
			fields=["docstatus", "received_qty"],
			order_by="creation desc",
			limit=1,
		)
	assert len(receipts) == 1
	assert receipts[0]["docstatus"] == 0
	assert receipts[0]["received_qty"] == scan_count
