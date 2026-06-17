# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest

from beam.beam.barcodes import create_beam_barcode
from beam.beam.doctype.beam_settings.beam_settings import get_doctypes_with_item_barcodes


@pytest.mark.order(20)
def test_get_doctypes_with_item_barcodes():
	doctypes = get_doctypes_with_item_barcodes()
	assert isinstance(doctypes, list)
	assert "Item" in doctypes
	assert "Warehouse" in doctypes
	# all returned values must be real doctypes
	for dt in doctypes:
		assert frappe.db.exists("DocType", dt), f"Stale DocField reference: '{dt}' does not exist"


def _make_item(item_code):
	if frappe.db.exists("Item", item_code):
		item = frappe.get_doc("Item", item_code)
		item.barcodes = []
		return item
	item = frappe.new_doc("Item")
	item.item_code = item_code
	item.item_name = item_code
	item.item_group = "All Item Groups"
	item.stock_uom = "Nos"
	item.is_stock_item = 1
	return item


@pytest.fixture()
def beam_settings():
	company = frappe.defaults.get_defaults().get("company")
	settings = frappe.get_doc("BEAM Settings", {"company": company})
	original = settings.auto_barcode_doctypes
	yield settings
	settings.auto_barcode_doctypes = original
	settings.save()


@pytest.mark.order(22)
def test_barcode_generated_when_doctype_allowed(beam_settings):
	beam_settings.auto_barcode_doctypes = '["Item", "Warehouse"]'
	beam_settings.save()

	item = _make_item("_Test Barcode Allow Item")
	create_beam_barcode(item)

	assert any(b.barcode_type == "Code128" for b in item.barcodes)


@pytest.mark.order(24)
def test_barcode_not_generated_when_doctype_not_allowed(beam_settings):
	beam_settings.auto_barcode_doctypes = '["Warehouse"]'
	beam_settings.save()

	item = _make_item("_Test Barcode Disallow Item")
	create_beam_barcode(item)

	assert not any(b.barcode_type == "Code128" for b in item.barcodes)


@pytest.mark.order(26)
def test_barcode_not_duplicated_when_code128_exists(beam_settings):
	beam_settings.auto_barcode_doctypes = '["Item", "Warehouse"]'
	beam_settings.save()

	item = _make_item("_Test Barcode Dedup Item")
	item.append("barcodes", {"barcode": "12345678901234567890", "barcode_type": "Code128"})
	create_beam_barcode(item)

	code128_barcodes = [b for b in item.barcodes if b.barcode_type == "Code128"]
	assert len(code128_barcodes) == 1
