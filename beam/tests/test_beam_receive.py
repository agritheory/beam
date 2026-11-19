# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

pytest_plugins = ["beam.tests.playwright_fixtures"]

# To test locally:
#  active the virtual environment
#  bench start, and then run:
#  pytest ./beam/tests/test_beam_receive.py --browser firefox --headed --disable-warnings

import re

import frappe
import pytest
from playwright.sync_api import expect

from beam.tests.playwright_utils import (
	error_toast_text,
	goto_beam_portal_route,
	open_first_beam_list_row,
	open_receive_row_for_item,
	order_id_from_beam_url,
	use_current_db_transaction,
	wait_for_docstatus,
	wait_for_purchase_receipt_items,
)

# NOTE: any navigation tests should be done using `expect(page).to_have_url` since
# `page.expect_navigation()` won't work with Beam's hash-based routes


@pytest.mark.order(310)
def test_scan_invalid_barcode(page):
	open_first_beam_list_row(page, "Receive", r"purchase-receipt/")
	order_id = order_id_from_beam_url(page.url)
	assert order_id

	# wait for items to load after navigation
	expect(page.locator("css=.box .beam_item-count").first).to_be_visible()
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


@pytest.mark.order(311)
def test_receive_without_scanning(page):
	"""Test trying to receive without scanning any items"""
	open_first_beam_list_row(page, "Receive", r"purchase-receipt/")
	order_id = order_id_from_beam_url(page.url)
	assert order_id

	# wait for items to load after navigation
	expect(page.locator("css=.box .beam_list-item").first).to_be_visible()
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


@pytest.mark.order(312)
def test_complete_partial_receipt(page):
	open_first_beam_list_row(page, "Receive", r"purchase-receipt/")
	order_id = order_id_from_beam_url(page.url)
	assert order_id

	expect(page.locator("css=.box .beam_list-item").first).to_be_visible()
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

	with use_current_db_transaction():
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

	page.get_by_text("SAVE", exact=True).click()
	assert not error_toast_text(page), "SAVE failed on Purchase Receipt"
	receipts = wait_for_purchase_receipt_items(order_id, item_code, min_count=1)
	assert receipts[0]["docstatus"] == 0
	assert receipts[0]["received_qty"] == 1
	pr_name = receipts[0]["parent"]

	page.get_by_role("button", name="SUBMIT", exact=True).click()
	assert not error_toast_text(page), "SUBMIT failed on Purchase Receipt"
	wait_for_docstatus("Purchase Receipt", pr_name, 1)
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


@pytest.mark.order(313)
def test_rapid_barcode_scanning(page):
	"""Test scanning multiple barcodes quickly"""
	open_receive_row_for_item(page, "Cloudberry", r"purchase-receipt/")
	order_id = order_id_from_beam_url(page.url)
	assert order_id

	expect(page.locator("css=.box .beam_list-item").first).to_be_visible()
	item = page.locator("css=.box .beam_list-item").first
	item_code, *others = item.inner_text().split("\n")
	assert item_code == "Cloudberry"
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
	assert not error_toast_text(page), "SAVE failed on Purchase Receipt"
	receipts = wait_for_purchase_receipt_items(
		order_id,
		item_code,
		min_count=1,
		docstatus=0,
		received_qty=scan_count,
	)
	assert len(receipts) == 1
	assert receipts[0]["docstatus"] == 0
	assert receipts[0]["received_qty"] == scan_count


@pytest.mark.order(339)
def test_edit_repeated_item_on_unsaved_receipt(page):
	"""Lines mapped from a Purchase Order have no name until saved; editing one must not update another."""
	with use_current_db_transaction():
		po = frappe.new_doc("Purchase Order")
		po.supplier = "Freedom Provisions"
		po.company = "Ambrosia Pie Company"
		po.schedule_date = frappe.utils.today()
		for _ in range(2):
			po.append("items", {"item_code": "Butter", "qty": 4, "rate": 1, "warehouse": "Receiving - APC"})
		po.insert()
		po.submit()
		frappe.db.commit()
		second_line = po.items[1].name

	pr_name = None
	try:
		goto_beam_portal_route(page, f"purchase-receipt/{po.name}")
		counts = page.locator(".box .beam_item-count")
		expect(counts).to_have_count(2)

		second = counts.nth(1).locator("[contenteditable]")
		second.click()
		page.keyboard.press("ControlOrMeta+A")
		page.keyboard.type("3", delay=150)
		page.keyboard.press("Enter")

		expect(counts.nth(0)).to_have_text(re.compile(r"^0/4"))
		expect(counts.nth(1)).to_have_text(re.compile(r"^3/4"))

		page.get_by_text("SAVE", exact=True).click()
		assert not error_toast_text(page), "SAVE failed on Purchase Receipt"
		receipts = wait_for_purchase_receipt_items(po.name, "Butter", min_count=1)
		pr_name = receipts[0]["parent"]
		with use_current_db_transaction():
			rows = frappe.get_all(
				"Purchase Receipt Item",
				filters={"parent": pr_name},
				fields=["purchase_order_item", "received_qty"],
			)
		assert [(row.purchase_order_item, row.received_qty) for row in rows] == [(second_line, 3)]
	finally:
		with use_current_db_transaction():
			if pr_name:
				frappe.delete_doc("Purchase Receipt", pr_name, force=True)
			frappe.get_doc("Purchase Order", po.name).cancel()
			frappe.db.commit()
