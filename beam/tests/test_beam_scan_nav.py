# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

pytest_plugins = ["beam.tests.playwright_fixtures"]

# To test locally:
#  active the virtual environment
#  bench start, and then run:
#  pytest ./beam/tests/test_beam_scan_nav.py --browser firefox --headed --disable-warnings

import re

import frappe
import pytest
from playwright.sync_api import expect

# NOTE: any navigation tests should be done using `expect(page).to_have_url` since
# `page.expect_navigation()` since the latter won't work with Beam's hash-based routes


@pytest.mark.order(301)
@pytest.mark.parametrize("route", ["Ship"])
def test_scan_item_barcode(page, route):
	# navigate in the following order: Home -> List -> Form
	page.get_by_text(route).click()
	expect(page).to_have_url(re.compile(rf"#/{route.lower()}"), timeout=15000)
	page.wait_for_load_state("networkidle")
	list_link = page.locator("a.beam_list-anchor").first
	expect(list_link).to_be_visible(timeout=15000)
	list_link.click()
	expect(page).to_have_url(re.compile(r"#/delivery-note"), timeout=15000)

	# wait for items to load after navigation
	expect(page.locator("css=.box .beam_list-item").first).to_be_visible()
	# find the first item in the list
	item = page.locator("css=.box .beam_list-item").first
	expect(item).to_be_visible(timeout=15000)
	item_name, *others = item.inner_text().split("\n")
	item_count = page.locator("css=.box .beam_item-count").first
	expect(item_count).to_have_text(re.compile("0/"), timeout=15000)

	# ensure that the item has barcodes
	barcodes = frappe.get_all(
		"Item Barcode", filters={"parenttype": "Item", "parent": item_name}, pluck="barcode"
	)
	assert len(barcodes) > 0

	# scan barcode and expect increment by 1
	with page.expect_request(
		lambda request: request.headers.get("x-frappe-cmd") == "beam.beam.scan.scan"
	):
		page.evaluate("barcode => scanner.simulate(window, barcode)", barcodes[0])
		expect(item_count).to_have_text(re.compile("1/"), timeout=15000)
