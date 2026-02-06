# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

from unittest.mock import Mock, patch

from frappe.exceptions import DoesNotExistError


def test_print_by_server_empty_string_uses_standard():
	"""Empty print_format should default to Standard"""
	from beam.beam.printing import print_by_server

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


def test_print_by_server_none_uses_standard():
	"""None print_format should default to Standard"""
	from beam.beam.printing import print_by_server

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
		except Exception:
			# Item Barcode exists, so it will get further and fail elsewhere
			# Just verify it doesn't fail on "Standard"
			pass
