# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest
from frappe.utils import today
from erpnext.accounts.doctype.sales_invoice.sales_invoice import make_delivery_note
from erpnext.stock.doctype.purchase_receipt.purchase_receipt import make_purchase_invoice


def _make_serials(series="WCC-.#####", qty=1):
	from frappe.model.naming import make_autoname

	return [make_autoname(series) for _ in range(qty)]


@pytest.mark.order(20)
def test_serial_number_scan():
	warehouse = "Storeroom - APC"
	supplier = "Unity Bakery Supply"
	item_code = "Whipped Cream Canister"
	serials = _make_serials(qty=3)
	pr = frappe.get_doc(
		{
			"doctype": "Purchase Receipt",
			"supplier": supplier,
			"posting_date": today(),
			"items": [
				{
					"item_code": item_code,
					"qty": 1,
					"received_qty": 1,
					"rate": 10,
					"warehouse": warehouse,
					"serial_no": serials[0],
					"use_serial_batch_fields": 1,
				}
			],
		}
	)
	pr.save()
	pr.submit()

	# Serial No scanning disabled
	settings = frappe.get_doc("BEAM Settings", "BEAM Settings")
	assert settings.scan_serial_no == 0
	scan = frappe.call(
		"beam.beam.scan.scan",
		**{"barcode": str(serials[0]), "context": {"listview": "Purchase Receipt"}}
	)
	assert scan is None

	# Serial No scanning enabled
	settings.scan_serial_no = 1
	settings.save()

	assert settings.scan_serial_no == 1
	scan = frappe.call(
		"beam.beam.scan.scan",
		**{"barcode": str(serials[0]), "context": {"listview": "Purchase Receipt"}}
	)
	assert scan[0]["action"] == "route"
	assert scan[0]["doctype"] == "Purchase Receipt"
	assert scan[0]["field"] == "Purchase Receipt"
	assert scan[0]["target"] == pr.name

	pi = frappe.get_doc(
		{
			"doctype": "Purchase Invoice",
			"supplier": supplier,
			"posting_date": today(),
			"update_stock": 1,
			"items": [
				{
					"item_code": item_code,
					"qty": 1,
					"received_qty": 1,
					"rate": 10,
					"warehouse": warehouse,
					"serial_no": serials[1],
					"use_serial_batch_fields": 1,
				}
			],
		}
	)
	pi.save()
	pi.submit()

	settings = frappe.get_doc("BEAM Settings", "BEAM Settings")
	settings.scan_serial_no = 1
	settings.save()
	scan = frappe.call(
		"beam.beam.scan.scan",
		**{"barcode": str(serials[1]), "context": {"listview": "Purchase Invoice"}}
	)
	assert scan[0]["action"] == "filter"
	assert scan[0]["doctype"] == "Purchase Invoice"
	assert scan[0]["field"] == "name"
	assert scan[0]["target"] == pi.name

	si = frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"customer": "Starfood Cafe",
			"posting_date": today(),
			"update_stock": 1,
			"items": [
				{
					"item_code": item_code,
					"qty": 1,
					"rate": 15,
					"warehouse": warehouse,
					"serial_no": serials[1],
					"use_serial_batch_fields": 1,
				}
			],
		}
	)
	si.save()
	si.submit()

	settings = frappe.get_doc("BEAM Settings", "BEAM Settings")
	settings.scan_serial_no = 1
	settings.save()
	scan = frappe.call(
		"beam.beam.scan.scan", **{"barcode": str(serials[1]), "context": {"listview": "Sales Invoice"}}
	)
	assert scan[0]["action"] == "filter"
	assert scan[0]["doctype"] == "Sales Invoice"
	assert scan[0]["field"] == "name"
	assert scan[0]["target"] == si.name
	# TODO: fix delivery note serial no scan
	dn = make_delivery_note(si.name)
	dn.posting_date = today()
	if dn.items and not dn.items[0].serial_no:
		dn.items[0].serial_no = serials[2]
	dn.save()
	dn.submit()

	settings = frappe.get_doc("BEAM Settings", "BEAM Settings")
	settings.scan_serial_no = 1
	settings.save()
	scan = frappe.call(
		"beam.beam.scan.scan", **{"barcode": str(serials[1]), "context": {"listview": "Delivery Note"}}
	)
	assert scan[0]["action"] == "filter"
	assert scan[0]["doctype"] == "Delivery Note"
	assert scan[0]["field"] == "name"
	assert scan[0]["target"] == dn.name
