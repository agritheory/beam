from unittest.mock import MagicMock, patch

import frappe
import pytest


@pytest.mark.skip()
def test_hooks_override(monkeypatch):
	hooks = frappe.get_hooks()
	hooks["beam_frm"] = {
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

	monkeypatch.setattr(frappe, "get_hooks", lambda x: hooks)

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
	assert scan[0].get("action") == "add_or_increment"
	assert scan[0].get("doctype") == "Delivery Note Item"
	assert scan[0].get("field") == "item_code"
	assert scan[0].get("target") == "Kaduka Key Lime Pie"
	assert scan[1].get("action") == "add_or_increment"
	assert scan[1].get("doctype") == "Delivery Note Item"
	assert scan[1].get("field") == "uom"
	assert scan[1].get("target") == "Nos"
