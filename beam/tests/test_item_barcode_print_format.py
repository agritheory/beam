# Copyright (c) 2025, AgriTheory and contributors
# Test for barcode generation in Item Barcode print format

import pytest

from beam.beam.barcodes import barcode128


@pytest.mark.parametrize("barcode_text", ["123456789012", "ITEM-00001", "987654321098"])
def test_item_barcode_print_format(barcode_text):
	# Generate barcode image in print format
	img_html = barcode128(barcode_text)
	assert img_html.startswith('<img src="data:image/png;base64,')
	assert "base64," in img_html
	assert img_html.endswith('"/>')
	# Optionally, check that the base64 string decodes to PNG
	import base64
	import re

	match = re.search(r"data:image/png;base64,([A-Za-z0-9+/=]+)", img_html)
	assert match, "No base64 PNG found in img tag"
	png_bytes = base64.b64decode(match.group(1))
	assert png_bytes[:8] == b"\x89PNG\r\n\x1a\n", "Not a PNG file"
