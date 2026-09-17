# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest
from frappe import get_hooks
from frappe.model.naming import make_autoname


@pytest.fixture()
def patch_frappe_get_hooks(monkeymodule, *args, **kwargs):
	def patched_hooks(*args, **kwargs):
		hooks = get_hooks(*args, **kwargs)
		if "beam_frm" in args:
			return {
				"Item": {
					"Delivery Note": [
						{
							"action": "add_or_increment",
							"doctype": "Delivery Note Item",
							"field": "item_code",
							"target": "target.item_code",
						},
						{
							"action": "add_or_increment",
							"doctype": "Delivery Note Item",
							"field": "uom",
							"target": "target.uom",
						},
					]
				}
			}
		if "beam_listview" in args:
			return {
				"Item": {
					"Delivery Note": [
						{"action": "filter", "doctype": "Delivery Note Item", "field": "item_code"},
						{"action": "filter", "doctype": "Packed Item", "field": "item_code"},
					],
				}
			}
		return hooks

	monkeymodule.setattr("frappe.get_hooks", patched_hooks)


@pytest.fixture()
def patch_frappe_get_hooks_serial_no(monkeymodule, *args, **kwargs):
	def patched_hooks(*args, **kwargs):
		hooks = get_hooks(*args, **kwargs)
		if "beam_frm" in args:
			return {
				"Serial No": {
					"Stock Entry": [
						{
							"action": "set_item_code_and_handling_unit",
							"doctype": "Stock Entry",
							"field": "item_code",
							"target": "target.item_code",
						},
					],
					"Quality Inspection": [
						{
							"action": "set_item_code_and_handling_unit",
							"doctype": "Quality Inspection",
							"field": "item_code",
							"target": "target.item_code",
						},
					],
				}
			}
		if "beam_listview" in args:
			return {
				"Serial No": {
					"Quality Inspection": [
						{"action": "filter", "doctype": "Quality Inspection", "field": "serial_no"}
					]
				}
			}
		return hooks

	monkeymodule.setattr("frappe.get_hooks", patched_hooks)


def _serial_no_without_sle(item_code):
	"""Create (if needed) a serialized item and a Serial No for it with no Stock
	Ledger Entry, reproducing a serial minted before its inward stock transaction
	is submitted (see issue #350)."""
	if not frappe.db.exists("Item", item_code):
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_code,
				"item_name": item_code,
				"item_group": "All Item Groups",
				"stock_uom": "Nos",
				"has_serial_no": 1,
				"is_stock_item": 1,
			}
		).insert(ignore_permissions=True)

	serial_no = make_autoname("BEAM-NOSLE-.#####")
	frappe.get_doc({"doctype": "Serial No", "serial_no": serial_no, "item_code": item_code}).insert(
		ignore_permissions=True
	)
	return serial_no


def _enable_scan_serial_no():
	company = frappe.defaults.get_defaults().get("company")
	settings = frappe.get_doc("BEAM Settings", {"company": company})
	settings.scan_serial_no = 1
	settings.save()


@pytest.mark.order(46)
def test_beam_frm_hooks_override(patch_frappe_get_hooks):
	item_barcode = frappe.get_value("Item Barcode", {"parent": "Kaduka Key Lime Pie"}, "barcode")
	dn = frappe.new_doc("Delivery Note")
	dn.customer = "Almacs Food Group"
	scan = frappe.call(
		"beam.beam.scan.scan",
		**{
			"barcode": str(item_barcode),
			"context": {"frm": dn.doctype, "doc": dn.as_dict()},
			"current_qty": 1,
		},
	)

	assert len(scan) == 2
	assert scan[0].get("action") == "add_or_increment"
	assert scan[0].get("doctype") == "Delivery Note Item"
	assert scan[0].get("field") == "item_code"
	assert scan[0].get("target") == "Kaduka Key Lime Pie"
	assert scan[1].get("action") == "add_or_increment"
	assert scan[1].get("doctype") == "Delivery Note Item"
	assert scan[1].get("field") == "uom"
	assert scan[1].get("target") == "Nos"


@pytest.mark.order(48)
def test_beam_listview_hooks_override(patch_frappe_get_hooks):
	item_barcode = frappe.get_value("Item Barcode", {"parent": "Kaduka Key Lime Pie"}, "barcode")
	scan = frappe.call(
		"beam.beam.scan.scan",
		**{"barcode": str(item_barcode), "context": {"listview": "Delivery Note"}, "current_qty": 1},
	)

	assert len(scan) == 2
	assert scan[0].get("action") == "filter"
	assert scan[0].get("doctype") == "Delivery Note Item"
	assert scan[0].get("field") == "item_code"
	assert scan[0].get("target") == "Kaduka Key Lime Pie"
	assert scan[1].get("action") == "filter"
	assert scan[1].get("doctype") == "Packed Item"
	assert scan[1].get("field") == "item_code"
	assert scan[1].get("target") == "Kaduka Key Lime Pie"


@pytest.mark.order(50)
@pytest.mark.parametrize("frm", ["Stock Entry", "Quality Inspection"])
def test_beam_frm_hooks_override_serial_no_without_sle(patch_frappe_get_hooks_serial_no, frm):
	# frm="Stock Entry" and frm="Quality Inspection" each used to be handled by
	# their own branch in get_form_action *before* has_frm_override was checked,
	# so a beam_frm override could never run for them when the serial had no
	# Stock Ledger Entry yet. Covers issue #350.
	_enable_scan_serial_no()
	item_code = "BEAM Test No-SLE Item"
	serial_no = _serial_no_without_sle(item_code)

	scan = frappe.call(
		"beam.beam.scan.scan",
		**{"barcode": serial_no, "context": {"frm": frm, "doc": None}, "current_qty": 1},
	)

	assert len(scan) == 1
	assert scan[0].get("action") == "set_item_code_and_handling_unit"
	assert scan[0].get("context", {}).get("item_code") == item_code
	assert scan[0].get("context", {}).get("stock_uom") == "Nos"
	# fields only populated from an existing Stock Ledger Entry must be absent
	assert "voucher_no" not in scan[0].get("context", {})


@pytest.mark.order(51)
def test_beam_listview_hooks_override_serial_no_without_sle(patch_frappe_get_hooks_serial_no):
	# get_list_action used to return [] as soon as get_serial_no() came back None,
	# before frappe.get_hooks("beam_listview") was even read. Covers issue #350.
	_enable_scan_serial_no()
	item_code = "BEAM Test No-SLE Item"
	serial_no = _serial_no_without_sle(item_code)

	scan = frappe.call(
		"beam.beam.scan.scan",
		**{"barcode": serial_no, "context": {"listview": "Quality Inspection"}, "current_qty": 1},
	)

	assert len(scan) == 1
	assert scan[0].get("action") == "filter"
	assert scan[0].get("doctype") == "Quality Inspection"
	assert scan[0].get("target") == serial_no
	assert scan[0].get("context") == serial_no


@pytest.mark.order(52)
def test_serial_no_scan_without_sle_and_without_override(monkeypatch):
	# With no beam_frm/beam_listview hook registered, a Serial No with no Stock
	# Ledger Entry must behave exactly as it did before issue #350 was fixed:
	# get_list_action returns [] and get_form_action still raises, since there is
	# no override to fall back on. Force frappe.get_hooks to report no overrides
	# so this doesn't depend on which other apps happen to be installed.
	def no_override_hooks(*args, **kwargs):
		if "beam_frm" in args or "beam_listview" in args:
			return {}
		return get_hooks(*args, **kwargs)

	monkeypatch.setattr("frappe.get_hooks", no_override_hooks)
	_enable_scan_serial_no()
	item_code = "BEAM Test No-SLE Item"
	serial_no = _serial_no_without_sle(item_code)

	scan = frappe.call(
		"beam.beam.scan.scan",
		**{"barcode": serial_no, "context": {"listview": "Quality Inspection"}, "current_qty": 1},
	)
	assert scan == []

	with pytest.raises(AttributeError):
		frappe.call(
			"beam.beam.scan.scan",
			**{
				"barcode": serial_no,
				"context": {"frm": "Quality Inspection", "doc": None},
				"current_qty": 1,
			},
		)
