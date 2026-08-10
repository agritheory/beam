# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest

from beam.beam.barcodes import create_beam_barcode
from beam.beam.doctype.beam_settings.beam_settings import get_doctypes_with_item_barcodes


@pytest.mark.order(20)
def test_barcode_generated_when_doctype_allowed(beam_settings):
	beam_settings.auto_barcode_doctypes = '["Item", "Warehouse"]'
	beam_settings.save()

	item = _make_item("_Test Barcode Allow Item")
	create_beam_barcode(item)

	assert any(b.barcode_type == "Code128" for b in item.barcodes)


@pytest.mark.order(24)
def test_barcode_not_duplicated_when_code128_exists(beam_settings):
	beam_settings.auto_barcode_doctypes = '["Item", "Warehouse"]'
	beam_settings.save()

	item = _make_item("_Test Barcode Dedup Item")
	item.append("barcodes", {"barcode": "12345678901234567890", "barcode_type": "Code128"})
	create_beam_barcode(item)

	code128_barcodes = [b for b in item.barcodes if b.barcode_type == "Code128"]
	assert len(code128_barcodes) == 1
