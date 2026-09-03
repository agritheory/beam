# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest
from erpnext.stock.doctype.stock_ledger_entry.stock_ledger_entry import (
	SerialNoInventoryDimensionError,
)
from frappe.utils import add_days, today

from beam.beam.handling_unit import common_inward_handling_unit, set_outbound_handling_units

WAREHOUSE = "Storeroom - APC"
OTHER_WAREHOUSE = "Kitchen - APC"
SUPPLIER = "Unity Bakery Supply"
CUSTOMER = "Longwoods Sandwich Shop"
ITEM = "Whipped Cream Canister"  # seeded with has_serial_no = 1, enable_handling_unit = 1


def receive_serials(serial_nos, posting_date=None, with_handling_unit=True):
	"""Receive `serial_nos` on a single Purchase Receipt row (so one handling unit).

	Returns the handling unit beam stamped on the row (None when `with_handling_unit`
	is False, i.e. handling units disabled for the item during the receipt).
	"""
	if not with_handling_unit:
		frappe.db.set_value("Item", ITEM, "enable_handling_unit", 0)
	try:
		pr = frappe.get_doc(
			{
				"doctype": "Purchase Receipt",
				"supplier": SUPPLIER,
				"set_posting_time": 1,
				"posting_date": posting_date or today(),
				"items": [
					{
						"item_code": ITEM,
						"qty": len(serial_nos),
						"received_qty": len(serial_nos),
						"rate": 10,
						"warehouse": WAREHOUSE,
						"serial_no": "\n".join(serial_nos),
						"use_serial_batch_fields": 1,
					}
				],
			}
		)
		pr.save()
		pr.submit()
		return pr.items[0].handling_unit
	finally:
		if not with_handling_unit:
			frappe.db.set_value("Item", ITEM, "enable_handling_unit", 1)


def receive_serial(serial_no, **kwargs):
	return receive_serials([serial_no], **kwargs)


def transfer_serial(serial_no, source_handling_unit, s_warehouse, t_warehouse):
	"""Move `serial_no` between warehouses; beam assigns a fresh handling unit on the
	inward leg. Returns that new handling unit."""
	se = frappe.get_doc(
		{
			"doctype": "Stock Entry",
			"stock_entry_type": "Material Transfer",
			"purpose": "Material Transfer",
			"company": frappe.defaults.get_defaults().get("company"),
			"set_posting_time": 1,
			"posting_date": today(),
			"items": [
				{
					"item_code": ITEM,
					"qty": 1,
					"s_warehouse": s_warehouse,
					"t_warehouse": t_warehouse,
					"serial_no": serial_no,
					"use_serial_batch_fields": 1,
					"handling_unit": source_handling_unit,
				}
			],
		}
	)
	se.save()
	se.submit()
	return se.items[0].to_handling_unit


def draft_delivery_note(serial_nos, posting_date=None, warehouse=WAREHOUSE):
	dn = frappe.get_doc(
		{
			"doctype": "Delivery Note",
			"customer": CUSTOMER,
			"set_posting_time": 1,
			"posting_date": posting_date or today(),
			"items": [
				{
					"item_code": ITEM,
					"qty": len(serial_nos),
					"rate": 10,
					"warehouse": warehouse,
					"serial_no": "\n".join(serial_nos),
					"use_serial_batch_fields": 1,
				}
			],
		}
	)
	dn.save()
	return dn


def draft_sales_invoice(serial_nos, warehouse=WAREHOUSE):
	si = frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"customer": CUSTOMER,
			"update_stock": 1,
			"set_posting_time": 1,
			"posting_date": today(),
			"items": [
				{
					"item_code": ITEM,
					"qty": len(serial_nos),
					"rate": 10,
					"warehouse": warehouse,
					"serial_no": "\n".join(serial_nos),
					"use_serial_batch_fields": 1,
				}
			],
		}
	)
	si.save()
	return si


@pytest.mark.order(71)
def test_single_serial_handling_unit_is_filled_by_hook_and_ships():
	handling_unit = receive_serial("WCC-OB-1")

	dn = draft_delivery_note(["WCC-OB-1"])
	dn.submit()  # before_submit hook fills handling_unit; ERPNext validation must pass

	assert dn.docstatus == 1
	assert dn.items[0].handling_unit == handling_unit
	assert frappe.get_doc("Delivery Note", dn.name).items[0].handling_unit == handling_unit


@pytest.mark.order(71)
def test_multiple_serials_in_one_handling_unit_ship_on_one_row():
	handling_unit = receive_serials(["WCC-OB-6A", "WCC-OB-6B", "WCC-OB-6C"])

	dn = draft_delivery_note(["WCC-OB-6A", "WCC-OB-6B", "WCC-OB-6C"])
	dn.submit()

	assert dn.docstatus == 1
	assert dn.items[0].handling_unit == handling_unit


@pytest.mark.order(71)
def test_uses_latest_handling_unit_after_a_transfer():
	hu_a = receive_serial("WCC-OB-7")
	hu_b = transfer_serial("WCC-OB-7", hu_a, WAREHOUSE, OTHER_WAREHOUSE)
	assert hu_b and hu_b != hu_a

	dn = draft_delivery_note(["WCC-OB-7"], warehouse=OTHER_WAREHOUSE)
	dn.submit()

	assert dn.docstatus == 1
	assert dn.items[0].handling_unit == hu_b


@pytest.mark.order(71)
def test_serials_in_different_handling_units_are_rejected():
	receive_serial("WCC-OB-2A")  # own Purchase Receipt -> own handling unit
	receive_serial("WCC-OB-2B")  # another Purchase Receipt -> a different handling unit

	dn = draft_delivery_note(["WCC-OB-2A", "WCC-OB-2B"])
	# hook cannot pick a single handling unit -> row stays empty -> ERPNext rejects
	with pytest.raises(SerialNoInventoryDimensionError):
		dn.submit()
	assert not dn.items[0].handling_unit


@pytest.mark.order(71)
def test_mixed_serials_with_and_without_handling_unit_are_rejected():
	receive_serial("WCC-OB-4A")  # has a handling unit
	receive_serial("WCC-OB-4B", with_handling_unit=False)  # has none

	dn = draft_delivery_note(["WCC-OB-4A", "WCC-OB-4B"])
	with pytest.raises(SerialNoInventoryDimensionError):
		dn.submit()
	assert not dn.items[0].handling_unit


@pytest.mark.order(71)
def test_serial_received_without_handling_unit_ships_without_one():
	assert receive_serial("WCC-OB-3", with_handling_unit=False) is None

	dn = draft_delivery_note(["WCC-OB-3"])
	dn.submit()  # expected dimension is "Not Set" on both sides -> ok

	assert dn.docstatus == 1
	assert not dn.items[0].handling_unit


@pytest.mark.order(71)
def test_sales_invoice_with_update_stock_is_filled_by_hook_and_submits():
	handling_unit = receive_serial("WCC-OB-8")

	si = draft_sales_invoice(["WCC-OB-8"])
	si.submit()

	assert si.docstatus == 1
	assert si.items[0].handling_unit == handling_unit


@pytest.mark.order(71)
def test_common_inward_handling_unit_respects_posting_datetime():
	handling_unit = receive_serial("WCC-OB-5", posting_date=today())

	as_of_today = common_inward_handling_unit(ITEM, ["WCC-OB-5"], f"{today()} 23:59:59")
	assert as_of_today == handling_unit

	# the receipt is dated after this -> not visible yet
	as_of_yesterday = common_inward_handling_unit(
		ITEM, ["WCC-OB-5"], f"{add_days(today(), -1)} 00:00:00"
	)
	assert as_of_yesterday is None


@pytest.mark.order(71)
def test_legacy_serial_no_field_is_resolved():
	handling_unit = receive_serials(["WCC-OB-L1", "WCC-OB-L2"])

	# rewrite the inward SLE to the pre-bundle shape: no bundle, newline-joined serials
	sle_name = frappe.db.get_value(
		"Stock Ledger Entry", {"handling_unit": handling_unit, "actual_qty": (">", 0)}, "name"
	)
	frappe.db.set_value(
		"Stock Ledger Entry",
		sle_name,
		{"serial_and_batch_bundle": "", "serial_no": "WCC-OB-L1\nWCC-OB-L2"},
	)

	resolved = common_inward_handling_unit(
		ITEM, ["WCC-OB-L1", "WCC-OB-L2"], f"{today()} 23:59:59"
	)
	assert resolved == handling_unit


@pytest.mark.order(71)
def test_partial_resolution_returns_none():
	receive_serial("WCC-OB-P1")  # has a handling unit

	# one serial resolves, the other has no inward movement -> do not guess
	resolved = common_inward_handling_unit(
		ITEM, ["WCC-OB-P1", "WCC-OB-NEVER-RECEIVED"], f"{today()} 23:59:59"
	)
	assert resolved is None


@pytest.mark.order(71)
def test_sales_invoice_without_update_stock_is_untouched():
	receive_serial("WCC-OB-NS")

	si = frappe.get_doc(
		{
			"doctype": "Sales Invoice",
			"customer": CUSTOMER,
			"update_stock": 0,
			"set_posting_time": 1,
			"posting_date": today(),
			"items": [
				{
					"item_code": ITEM,
					"qty": 1,
					"rate": 10,
					"warehouse": WAREHOUSE,
					"serial_no": "WCC-OB-NS",
					"use_serial_batch_fields": 1,
				}
			],
		}
	)
	si.save()

	set_outbound_handling_units(si)
	assert not si.items[0].handling_unit


@pytest.mark.order(71)
def test_explicit_handling_unit_is_not_overwritten():
	receive_serial("WCC-OB-9")  # lives in one handling unit

	other_hu = frappe.new_doc("Handling Unit")
	other_hu.save()

	dn = draft_delivery_note(["WCC-OB-9"])
	dn.items[0].handling_unit = other_hu.name

	# hook must leave the explicit value alone -> ERPNext then rejects the mismatch
	with pytest.raises(SerialNoInventoryDimensionError):
		dn.submit()
	assert dn.items[0].handling_unit == other_hu.name
