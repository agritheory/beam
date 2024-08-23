import frappe
import pytest
from frappe import get_hooks


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


@pytest.mark.order(30)
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
		}
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


def test_beam_listview_hooks_override(patch_frappe_get_hooks):
	item_barcode = frappe.get_value("Item Barcode", {"parent": "Kaduka Key Lime Pie"}, "barcode")
	scan = frappe.call(
		"beam.beam.scan.scan",
		**{"barcode": str(item_barcode), "context": {"listview": "Delivery Note"}, "current_qty": 1}
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
