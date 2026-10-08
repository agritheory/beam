# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

pytest_plugins = ["beam.tests.playwright_fixtures"]

import re

import frappe
import pytest
from playwright.sync_api import expect

from beam.tests.playwright_utils import (
	open_beam_form_page,
	simulate_scan,
	use_current_db_transaction,
)

WAREHOUSE = "Baked Goods - APC"
RECONCILIATION_ROW = ".reconciliation-list-row"


def fill_warehouse_dropdown(page, label: str, value: str):
	wrapper = page.locator(".input-wrapper", has=page.locator("label", has_text=label))
	inp = wrapper.locator("input")
	inp.click()
	inp.fill(value)
	page.wait_for_timeout(300)
	result = wrapper.locator("li.autocomplete-result", has_text=value).first
	result.wait_for(state="visible")
	result.click()


def open_reconciliation_page(page):
	open_beam_form_page(
		page, "Reconciliation", r"#/stock-reconciliation", ".reconciliation .dropdown-container input"
	)


def select_reconciliation_warehouse(page):
	fill_warehouse_dropdown(page, "Warehouse", WAREHOUSE)
	expect(page.locator(RECONCILIATION_ROW).first).to_be_visible(timeout=20000)


def skip_count_button(page, row):
	return row.get_by_role("button", name="Skip counting this item")


@pytest.mark.order(325)
def test_reconciliation_remove_row(page):
	open_reconciliation_page(page)
	select_reconciliation_warehouse(page)

	rows = page.locator(RECONCILIATION_ROW)
	initial_count = rows.count()
	assert initial_count >= 2, "Need at least two warehouse rows to test removal"

	first_row = rows.first
	removed_item = first_row.locator("label.beam--bold").inner_text()
	skip_count_button(page, first_row).click()

	expect(page.locator(RECONCILIATION_ROW)).to_have_count(initial_count - 1)
	expect(page.locator(RECONCILIATION_ROW, has_text=removed_item)).to_have_count(0)


@pytest.mark.order(326)
def test_reconciliation_save_omits_removed_row(page):
	open_reconciliation_page(page)
	select_reconciliation_warehouse(page)

	rows = page.locator(RECONCILIATION_ROW)
	assert rows.count() >= 2

	removed_row = rows.last
	removed_item = removed_row.locator("label.beam--bold").inner_text()
	skip_count_button(page, removed_row).click()

	with use_current_db_transaction():
		barcodes = frappe.get_all(
			"Item Barcode",
			filters={"parent": "Ambrosia Pie"},
			pluck="barcode",
			limit=1,
		)
		assert barcodes, "Ambrosia Pie must have a barcode for scan"

	ambrosia_row = page.locator(RECONCILIATION_ROW, has_text="Ambrosia Pie")
	expect(ambrosia_row).to_have_count(1)
	simulate_scan(page, barcodes[0])
	expect(ambrosia_row.locator(".beam_item-count")).to_contain_text(re.compile(r"\b1\b"))

	page.get_by_text("SAVE", exact=True).click()
	expect(page.get_by_text("not counted", exact=False)).to_be_visible()
	page.get_by_text("Save counted only", exact=True).click()
	page.wait_for_timeout(1000)

	with use_current_db_transaction():
		reconciliations = frappe.get_all(
			"Stock Reconciliation",
			filters={"docstatus": 0, "owner": "support@agritheory.dev"},
			fields=["name"],
			order_by="creation desc",
			limit=1,
		)
		assert reconciliations, "Expected a draft Stock Reconciliation after save"
		reconciliation_name = reconciliations[0]["name"]

		line_items = frappe.get_all(
			"Stock Reconciliation Item",
			filters={"parent": reconciliation_name},
			fields=["item_code", "qty"],
		)
		item_codes = {row["item_code"] for row in line_items}
		assert "Ambrosia Pie" in item_codes
		assert removed_item not in item_codes
		ambrosia_qty = next(row["qty"] for row in line_items if row["item_code"] == "Ambrosia Pie")
		assert ambrosia_qty == 1
