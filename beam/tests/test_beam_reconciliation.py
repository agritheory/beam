# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

pytest_plugins = ["beam.tests.playwright_fixtures"]

# To test locally:
#  activate the virtual environment
#  bench start, and then run:
#  pytest ./beam/tests/test_beam_reconciliation.py --browser firefox --headed --disable-warnings

import frappe
import pytest
from playwright.sync_api import expect

from beam.beam.barcodes import create_beam_barcode
from beam.tests.playwright_utils import open_beam_form_page, simulate_scan

WAREHOUSE = "Storeroom - APC"
WAREHOUSE_INPUT = ".reconciliation .input-wrapper input"


def warehouse_barcode(warehouse: str) -> str:
	barcode = frappe.get_value(
		"Item Barcode", {"parenttype": "Warehouse", "parent": warehouse}, "barcode"
	)
	if barcode:
		return str(barcode)

	warehouse_doc = frappe.get_doc("Warehouse", warehouse)
	create_beam_barcode(warehouse_doc)
	warehouse_doc.save()
	frappe.db.commit()
	return str(warehouse_doc.barcodes[0].barcode)


@pytest.mark.order(360)
def test_scan_warehouse_sets_reconciliation_warehouse(page):
	open_beam_form_page(page, "Reconciliation", r"#/stock-reconciliation", WAREHOUSE_INPUT)

	barcode = warehouse_barcode(WAREHOUSE)
	simulate_scan(page, barcode)

	expect(page.locator(WAREHOUSE_INPUT)).to_have_value(WAREHOUSE)
