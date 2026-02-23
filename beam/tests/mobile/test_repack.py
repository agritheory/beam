# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest
from playwright.sync_api import expect

from beam.tests.test_utils import use_current_db_transaction


def fill_warehouse_dropdown(page, label: str, value: str):
	wrapper = page.locator(".input-wrapper", has=page.locator("label", has_text=label))
	inp = wrapper.locator("input")
	inp.click()
	inp.fill(value)
	page.wait_for_timeout(300)
	result = wrapper.locator("li.autocomplete-result", has_text=value).first
	result.wait_for(state="visible")
	result.click()


@pytest.mark.order(1)
def test_repack_items_manually(page):
	page.get_by_text("Repack").click()
	page.wait_for_load_state("networkidle")
	assert "/repack" in page.url

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

		warehouse = frappe.get_all(
			"Warehouse",
			filters={"is_group": 0, "company": "Ambrosia Pie Company"},
			pluck="name",
			limit=1,
		)[0]

	with page.expect_request(
		lambda request: request.headers.get("x-frappe-cmd") == "beam.beam.scan.scan"
	):
		page.evaluate("barcode => scanner.simulate(window, barcode)", barcode)
	page.wait_for_timeout(800)

	page.get_by_role("button", name="+").click()
	page.wait_for_timeout(200)

	fill_warehouse_dropdown(page, "Source Warehouse", warehouse)

	page.get_by_role("button", name="ADD", exact=True).click()
	page.wait_for_timeout(500)
	expect(page.locator("css=.beam_list-item").first).to_be_visible()

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
	assert entries, "Expected a draft Stock Entry after SAVE"

	page.get_by_role("button", name="REPACK", exact=True).click()
	page.wait_for_timeout(1500)

	with use_current_db_transaction():
		submitted = frappe.get_all(
			"Stock Entry",
			filters={"name": entries[0]["name"], "docstatus": 1},
			fields=["name", "docstatus"],
		)
	assert submitted, f"Expected Stock Entry {entries[0]['name']} to be submitted after REPACK"


@pytest.mark.order(2)
def test_repack_using_bom(page):
	page.get_by_text("Repack").click()
	page.wait_for_load_state("networkidle")
	assert "/repack" in page.url

	with use_current_db_transaction():
		boms = frappe.get_all(
			"BOM",
			filters={"is_active": 1, "is_default": 1, "docstatus": 1},
			pluck="name",
			limit=1,
		)
		assert boms, "No active default BOM found in test data"
		bom_name = boms[0]

		warehouse = frappe.get_all(
			"Warehouse",
			filters={"is_group": 0, "company": "Ambrosia Pie Company"},
			pluck="name",
			limit=1,
		)[0]

	fill_warehouse_dropdown(page, "BOM (Optional)", bom_name)
	page.wait_for_timeout(1000)

	expect(page.locator("css=.beam_list-item").first).to_be_visible()

	fill_warehouse_dropdown(page, "Target Warehouse", warehouse)

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
	assert entries, "Expected a draft Stock Entry to be created from BOM repack"


@pytest.mark.order(3)
def test_scan_item_for_repack(page):
	page.get_by_text("Repack").click()
	page.wait_for_load_state("networkidle")
	assert "/repack" in page.url

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

	with page.expect_request(
		lambda request: request.headers.get("x-frappe-cmd") == "beam.beam.scan.scan"
	):
		page.evaluate("barcode => scanner.simulate(window, barcode)", barcode)
	page.wait_for_timeout(800)

	item_wrapper = page.locator(
		".input-wrapper", has=page.locator("label", has_text="Item to Repack")
	)
	expect(item_wrapper.locator("input")).to_have_value(item_code)

	qty_input = page.locator("input.aform_input-field[type='number']")
	expect(qty_input).to_have_value("1")

	with page.expect_request(
		lambda request: request.headers.get("x-frappe-cmd") == "beam.beam.scan.scan"
	):
		page.evaluate("barcode => scanner.simulate(window, barcode)", barcode)
	page.wait_for_timeout(800)

	expect(qty_input).to_have_value("2")


@pytest.mark.order(4)
def test_clear_repack_form(page):
	page.get_by_text("Repack").click()
	page.wait_for_load_state("networkidle")
	assert "/repack" in page.url

	with use_current_db_transaction():
		item_barcodes = frappe.get_all(
			"Item Barcode",
			filters={"parenttype": "Item"},
			fields=["parent", "barcode"],
			limit=1,
		)
		assert item_barcodes, "No Item barcodes found in test data"
		barcode = item_barcodes[0]["barcode"]

		warehouse = frappe.get_all(
			"Warehouse",
			filters={"is_group": 0, "company": "Ambrosia Pie Company"},
			pluck="name",
			limit=1,
		)[0]

	with page.expect_request(
		lambda request: request.headers.get("x-frappe-cmd") == "beam.beam.scan.scan"
	):
		page.evaluate("barcode => scanner.simulate(window, barcode)", barcode)
	page.wait_for_timeout(800)

	page.get_by_role("button", name="+").click()
	fill_warehouse_dropdown(page, "Source Warehouse", warehouse)

	page.get_by_role("button", name="ADD", exact=True).click()
	page.wait_for_timeout(500)

	expect(page.locator("css=.beam_list-item").first).to_be_visible()
	expect(page.get_by_role("button", name="CLEAN", exact=True)).to_be_visible()

	page.get_by_role("button", name="CLEAN", exact=True).click()
	page.wait_for_timeout(500)

	expect(page.get_by_text("Scan Items, Select Warehouses, and Set Qty to Begin")).to_be_visible()

	expect(page.get_by_role("button", name="CLEAN", exact=True)).to_be_hidden()


@pytest.mark.order(5)
def test_repack_validation_single_warehouse_direction(page):
	page.get_by_text("Repack").click()
	page.wait_for_load_state("networkidle")
	assert "/repack" in page.url

	with use_current_db_transaction():
		item_barcodes = frappe.get_all(
			"Item Barcode",
			filters={"parenttype": "Item"},
			fields=["parent", "barcode"],
			limit=1,
		)
		assert item_barcodes, "No Item barcodes found in test data"
		barcode = item_barcodes[0]["barcode"]

		warehouses = frappe.get_all(
			"Warehouse",
			filters={"is_group": 0, "company": "Ambrosia Pie Company"},
			pluck="name",
			limit=2,
		)
		assert len(warehouses) >= 2, "Need at least 2 warehouses for this test"

	with page.expect_request(
		lambda request: request.headers.get("x-frappe-cmd") == "beam.beam.scan.scan"
	):
		page.evaluate("barcode => scanner.simulate(window, barcode)", barcode)
	page.wait_for_timeout(800)

	page.get_by_role("button", name="+").click()

	fill_warehouse_dropdown(page, "Source Warehouse", warehouses[0])
	fill_warehouse_dropdown(page, "Target Warehouse", warehouses[1])

	page.get_by_role("button", name="ADD", exact=True).click()
	page.wait_for_timeout(500)

	expect(page.get_by_text("Please select only source or target warehouse")).to_be_visible()

	expect(page.get_by_text("Scan Items, Select Warehouses, and Set Qty to Begin")).to_be_visible()
