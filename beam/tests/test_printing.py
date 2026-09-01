# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

from unittest.mock import Mock, patch

import frappe
import pytest
from frappe.exceptions import DoesNotExistError

from beam.beam.printing import print_by_server


@pytest.mark.order(100)
def test_print_by_server_empty_string_uses_standard():
	"""Empty print_format should default to Standard"""
	mock_cups = Mock()
	mock_cups.IPPError = Exception
	with patch("beam.beam.printing.cups", mock_cups):
		try:
			print_by_server(
				doctype="Item",
				name="Ambrosia Pie",
				printer_setting="Kitchen Printer",
				print_format="",
			)
		except DoesNotExistError as e:
			# Should fail trying to get "Standard" print format
			assert "Standard" in str(e)


@pytest.mark.order(102)
def test_print_by_server_none_uses_standard():
	"""None print_format should default to Standard"""
	mock_cups = Mock()
	mock_cups.IPPError = Exception
	with patch("beam.beam.printing.cups", mock_cups):
		try:
			print_by_server(
				doctype="Item",
				name="Ambrosia Pie",
				printer_setting="Kitchen Printer",
				print_format=None,
			)
		except DoesNotExistError as e:
			# Should fail trying to get "Standard" print format
			assert "Standard" in str(e)


@pytest.mark.order(104)
def test_print_by_server_explicit_format():
	"""Explicit print_format should be used"""
	from beam.beam.printing import print_by_server

	mock_cups = Mock()
	mock_cups.IPPError = Exception
	with patch("beam.beam.printing.cups", mock_cups):
		try:
			print_by_server(
				doctype="Item",
				name="Ambrosia Pie",
				printer_setting="Kitchen Printer",
				print_format="Item Barcode",
			)
		except Exception as e:
			# Should NOT fail on "Standard" - should use explicit format
			assert "Standard" not in str(e), "Should use explicit format, not Standard"


@pytest.mark.order(106)
def test_print_by_server_with_serialized_doc():
	"""Serialized doc should be properly deserialized as full document instance"""
	# Get a real item doc and serialize it like the frontend would
	item = frappe.get_doc("Item", "Ambrosia Pie")
	serialized_doc = frappe.as_json(item.as_dict())

	mock_cups = Mock()
	mock_cups.IPPError = Exception
	with patch("beam.beam.printing.cups", mock_cups):
		try:
			print_by_server(
				doctype="Item",
				name="Ambrosia Pie",
				printer_setting="Kitchen Printer",
				print_format="Item Barcode",
				doc=serialized_doc,  # Pass as JSON string
			)
		except Exception as e:
			# Should not fail with AttributeError about 'in_print'
			assert "in_print" not in str(e)
			assert not isinstance(e, AttributeError)
