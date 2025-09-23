# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest

from beam.tests.test_handling_unit import submit_all_purchase_receipts


@pytest.mark.order(20)
def test_serial_number_scan():
	submit_all_purchase_receipts()

	serial_nos = frappe.get_all("Serial No", filters={"item_code": "Sugar"}, pluck="name")
	assert len(serial_nos) > 0

	# Serial No scanning disabled
	settings = frappe.get_doc("BEAM Settings", "BEAM Settings")
	assert settings.scan_serial_no == 0
	scan = frappe.call(
		"beam.beam.scan.scan",
		**{"barcode": str(serial_nos[0]), "context": {"listview": "Purchase Invoice"}}
	)
	assert scan is None

	# Serial No scanning enabled
	settings.scan_serial_no = 1
	settings.save()
	assert settings.scan_serial_no == 1
	scan = frappe.call(
		"beam.beam.scan.scan",
		**{"barcode": str(serial_nos[0]), "context": {"listview": "Purchase Invoice"}}
	)
	assert scan[0]["action"] == "filter"
	assert scan[0]["doctype"] == "Purchase Invoice"
	assert scan[0]["field"] == "name"
