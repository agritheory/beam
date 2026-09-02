# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

pytest_plugins = ["beam.tests.playwright_fixtures"]

import frappe
import pytest
from playwright.sync_api import expect

from beam.tests.playwright_utils import (
	error_toast_text,
	open_beam_form_page,
	simulate_scan,
	use_current_db_transaction,
)

REPACK_QTY_INPUT = "input.aform_input-field[type='number']"


def fill_warehouse_dropdown(page, label: str, value: str):
	wrapper = page.locator(".input-wrapper", has=page.locator("label", has_text=label))
	inp = wrapper.locator("input")
	inp.click()
	inp.fill(value)
	page.wait_for_timeout(300)
	result = wrapper.locator("li.autocomplete-result", has_text=value).first
	result.wait_for(state="visible")
	result.click()


def open_repack_page(page):
	open_beam_form_page(page, "Repack", r"#/repack", REPACK_QTY_INPUT)


def repack_item_input(page):
	wrapper = page.locator(".input-wrapper", has=page.locator("label", has_text="Item to Repack"))
	return wrapper.locator("input")


def scan_into_repack(page, barcode: str, item_code: str):
	"""Scan an item and confirm the form actually consumed it.

	A scan the page never received leaves the form untouched, which otherwise
	surfaces several steps later as a rejected ADD or a missing Stock Entry.
	"""
	simulate_scan(page, barcode)
	expect(repack_item_input(page)).to_have_value(item_code)


@pytest.fixture(autouse=True, scope="module")
def disable_handling_unit_for_tests():
	"""Disable handling unit validation for repack tests in this module only."""
	items = frappe.get_all("Item", filters={"enable_handling_unit": 1}, pluck="name")
	try:
		for item in items:
			frappe.db.set_value("Item", item, "enable_handling_unit", 0)
		frappe.db.commit()
		yield
	finally:
		for item in items:
			frappe.db.set_value("Item", item, "enable_handling_unit", 1)
		frappe.db.commit()


@pytest.mark.order(320)
def test_repack_items_manually(page):
	open_repack_page(page)

	with use_current_db_transaction():
		source_barcode = frappe.get_all(
			"Item Barcode",
			filters={"parent": "Butter"},
			pluck="barcode",
			limit=1,
		)
		assert source_barcode, "Butter must have a barcode"

		finished_barcode = frappe.get_all(
			"Item Barcode",
			filters={"parent": "Ambrosia Pie"},
			pluck="barcode",
			limit=1,
		)
		assert finished_barcode, "Ambrosia Pie must have a barcode"

		source_wh = "Refrigerator - APC"
		target_wh = "Baked Goods - APC"

	qty_input = page.locator(REPACK_QTY_INPUT)
	expect(qty_input).to_have_value("0")

	scan_into_repack(page, source_barcode[0], "Butter")

	expect(qty_input).to_have_value("1")

	page.get_by_role("button", name="+").click()

	expect(qty_input).to_have_value("2")

	page.get_by_role("button", name="-").click()

	expect(qty_input).to_have_value("1")

	fill_warehouse_dropdown(page, "Source Warehouse", source_wh)
	page.get_by_role("button", name="ADD", exact=True).click()

	expect(page.locator("css=.beam_list-item").first).to_be_visible()

	scan_into_repack(page, finished_barcode[0], "Ambrosia Pie")

	page.get_by_role("button", name="+").click()
	fill_warehouse_dropdown(page, "Target Warehouse", target_wh)
	page.get_by_role("button", name="ADD", exact=True).click()

	expect(page.locator("css=.beam_list-item").nth(1)).to_be_visible()

	page.get_by_role("button", name="SAVE", exact=True).click()
	page.wait_for_timeout(1500)

	with use_current_db_transaction():
		entries = frappe.get_all(
			"Stock Entry",
			filters={"stock_entry_type": "Repack", "docstatus": 0},
			fields=["name"],
			order_by="creation desc",
			limit=1,
		)
	assert entries, "Expected draft Stock Entry to be created"
	stock_entry_name = entries[0]["name"]

	page.get_by_role("button", name="REPACK", exact=True).click()
	page.wait_for_timeout(1500)

	with use_current_db_transaction():
		submitted = frappe.get_all(
			"Stock Entry",
			filters={"name": stock_entry_name, "docstatus": 1},
			fields=["name"],
		)

	assert submitted, f"Expected Stock Entry {stock_entry_name} to be submitted"


@pytest.mark.order(321)
def test_repack_using_bom(page):
	open_repack_page(page)

	bom_name = "BOM-Gooseberry Pie Filling-001"
	target_wh = "Refrigerator - APC"

	with use_current_db_transaction():
		finished_barcode = frappe.get_all(
			"Item Barcode",
			filters={"parent": "Gooseberry Pie"},
			pluck="barcode",
			limit=1,
		)
		assert finished_barcode, "Gooseberry Pie must have a barcode"

	scan_into_repack(page, finished_barcode[0], "Gooseberry Pie")

	page.get_by_role("button", name="+").click()
	page.wait_for_timeout(300)

	fill_warehouse_dropdown(page, "BOM (Optional)", bom_name)
	page.wait_for_timeout(1000)

	fill_warehouse_dropdown(page, "Target Warehouse", target_wh)

	page.get_by_role("button", name="ADD", exact=True).click()
	page.wait_for_timeout(1000)

	page.get_by_role("button", name="SAVE", exact=True).click()
	page.wait_for_timeout(1500)

	rejected = error_toast_text(page)
	assert rejected is None, f"SAVE was rejected: {rejected}"

	with use_current_db_transaction():
		entries = frappe.get_all(
			"Stock Entry",
			filters={"stock_entry_type": "Repack", "docstatus": 0},
			fields=["name"],
			order_by="creation desc",
			limit=1,
		)
	assert entries, "Expected a draft Stock Entry to be created from BOM repack"


@pytest.mark.order(322)
def test_scan_item_for_repack(page):
	open_repack_page(page)

	with use_current_db_transaction():
		item_barcodes = frappe.get_all(
			"Item Barcode",
			filters={"parenttype": "Item"},
			fields=["parent", "barcode"],
			limit=1,
		)
		assert item_barcodes, "No Item barcodes found in test data"
	item_code = item_barcodes[0]["parent"]
	barcode = item_barcodes[0]["barcode"]

	scan_into_repack(page, barcode, item_code)

	qty_input = page.locator(REPACK_QTY_INPUT)
	expect(qty_input).to_have_value("1")

	scan_into_repack(page, barcode, item_code)

	expect(qty_input).to_have_value("2")


@pytest.mark.order(323)
def test_clear_repack_form(page):
	open_repack_page(page)

	with use_current_db_transaction():
		# Named fixture data rather than an unordered LIMIT 1. This test needs a
		# pair that ADD accepts, and test_repack_items_manually proves this one is;
		# an arbitrary first row is whatever the table happens to return and
		# changes when the site is reseeded.
		source_barcode = frappe.get_all(
			"Item Barcode",
			filters={"parent": "Butter"},
			pluck="barcode",
			limit=1,
		)
		assert source_barcode, "Butter must have a barcode"
		barcode = source_barcode[0]
		warehouse = "Refrigerator - APC"

	scan_into_repack(page, barcode, "Butter")

	page.get_by_role("button", name="+").click()
	fill_warehouse_dropdown(page, "Source Warehouse", warehouse)

	page.get_by_role("button", name="ADD", exact=True).click()
	page.wait_for_timeout(500)

	rejected = error_toast_text(page)
	assert rejected is None, f"ADD was rejected: {rejected}"

	expect(page.locator("css=.beam_list-item").first).to_be_visible()
	expect(page.get_by_role("button", name="CLEAN", exact=True)).to_be_visible()

	page.get_by_role("button", name="CLEAN", exact=True).click()
	page.wait_for_timeout(500)

	expect(page.get_by_text("Scan Items, Select Warehouses, and Set Qty to Begin")).to_be_visible()

	expect(page.get_by_role("button", name="CLEAN", exact=True)).to_be_hidden()


@pytest.mark.order(324)
def test_repack_validation_single_warehouse_direction(page):
	open_repack_page(page)

	with use_current_db_transaction():
		item_barcodes = frappe.get_all(
			"Item Barcode",
			filters={"parenttype": "Item"},
			fields=["parent", "barcode"],
			limit=1,
		)
		assert item_barcodes, "No Item barcodes found in test data"
		item_code = item_barcodes[0]["parent"]
		barcode = item_barcodes[0]["barcode"]

		warehouses = frappe.get_all(
			"Warehouse",
			filters={"is_group": 0, "company": "Ambrosia Pie Company"},
			pluck="name",
			limit=2,
		)
		assert len(warehouses) >= 2, "Need at least 2 warehouses for this test"

	scan_into_repack(page, barcode, item_code)

	page.get_by_role("button", name="+").click()

	fill_warehouse_dropdown(page, "Source Warehouse", warehouses[0])
	fill_warehouse_dropdown(page, "Target Warehouse", warehouses[1])

	page.get_by_role("button", name="ADD", exact=True).click()
	page.wait_for_timeout(500)

	expect(page.get_by_text("Please select only source or target warehouse")).to_be_visible()

	expect(page.get_by_text("Scan Items, Select Warehouses, and Set Qty to Begin")).to_be_visible()
