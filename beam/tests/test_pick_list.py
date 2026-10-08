# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest
from erpnext.manufacturing.doctype.work_order.work_order import create_pick_list
from frappe.utils import flt

COMPANY = "Ambrosia Pie Company"
SETTINGS = COMPANY


def build_butter_pick_list():
	"""One-line Butter pick for a fresh Pie Crust work order (qty 1)."""
	bom_no = frappe.db.get_value("BOM", {"item": "Pie Crust", "docstatus": 1, "is_active": 1}, "name")
	wo = frappe.new_doc("Work Order")
	wo.production_item = "Pie Crust"
	wo.bom_no = bom_no
	wo.qty = 1
	wo.company = COMPANY
	wo.wip_warehouse = "Kitchen - APC"
	wo.fg_warehouse = frappe.db.get_single_value("Manufacturing Settings", "default_fg_warehouse")
	wo.planned_start_date = frappe.utils.getdate()
	wo.get_items_and_operations_from_bom()
	wo.save()
	wo.submit()

	receipt = frappe.new_doc("Stock Entry")
	receipt.stock_entry_type = receipt.purpose = "Material Receipt"
	receipt.append(
		"items",
		{
			"item_code": "Butter",
			"qty": 2,
			"uom": "Pound",
			"t_warehouse": "Refrigerator - APC",
			"basic_rate": 4.50,
			"expense_account": "5119 - Stock Adjustment - APC",
		},
	)
	receipt.save()
	receipt.submit()

	pick_list = create_pick_list(wo.name, for_qty=1)
	pick_list.scan_mode = 1
	for location in pick_list.locations:
		location.picked_qty = location.stock_qty
	pick_list.save()
	return pick_list, wo


@pytest.mark.order(26)
def test_pick_list_submit_without_stock_entry_setting():
	"""
	Submitting a pick list leaves stock in place when the setting is off.

	| Account           | Stock Ledger | Debit | Credit | Warehouse           |
	| ----------------- | ------------ | ----- | ------ | --------------------- |
	| (no movement)     |              |       |        | Refrigerator - APC    |
	"""
	frappe.db.set_value("BEAM Settings", SETTINGS, "create_stock_entry_on_pick_list_submit", 0)
	pick_list, wo = build_butter_pick_list()
	butter_bin_before = frappe.db.get_value(
		"Bin", {"item_code": "Butter", "warehouse": "Refrigerator - APC"}, "actual_qty"
	)
	existing_entries = set(
		frappe.get_all("Stock Entry", filters={"work_order": wo.name, "docstatus": 1}, pluck="name")
	)

	pick_list.submit()

	new_entries = set(
		frappe.get_all("Stock Entry", filters={"work_order": wo.name, "docstatus": 1}, pluck="name")
	)
	butter_bin_after = frappe.db.get_value(
		"Bin", {"item_code": "Butter", "warehouse": "Refrigerator - APC"}, "actual_qty"
	)
	assert new_entries == existing_entries
	assert butter_bin_after == butter_bin_before

	frappe.db.set_value("BEAM Settings", SETTINGS, "create_stock_entry_on_pick_list_submit", 0)


@pytest.mark.order(27)
def test_pick_list_submit_creates_material_transfer_for_manufacture():
	"""
	Pick list submit with setting on moves Butter to Kitchen WIP.

	| Account           | Stock Ledger | Debit | Credit | Warehouse           |
	| ----------------- | ------------ | ----- | ------ | --------------------- |
	| Stock in Hand     | -1 lb Butter |       | $4.50  | Refrigerator - APC    |
	| Stock in Hand     | +1 lb Butter | $4.50 |        | Kitchen - APC         |
	"""
	frappe.db.set_value("BEAM Settings", SETTINGS, "create_stock_entry_on_pick_list_submit", 1)
	pick_list, wo = build_butter_pick_list()
	transferred_before = frappe.db.get_value(
		"Work Order Item", {"parent": wo.name, "item_code": "Butter"}, "transferred_qty"
	)

	pick_list.submit()

	transferred_after = frappe.db.get_value(
		"Work Order Item", {"parent": wo.name, "item_code": "Butter"}, "transferred_qty"
	)
	assert flt(transferred_after) > flt(transferred_before)

	sles = frappe.get_all(
		"Stock Ledger Entry",
		filters={
			"item_code": "Butter",
			"voucher_type": "Stock Entry",
			"docstatus": 1,
		},
		fields=["warehouse", "actual_qty", "stock_value_difference"],
		order_by="creation desc",
		limit=2,
	)
	warehouses = {row.warehouse for row in sles}
	assert "Refrigerator - APC" in warehouses or "Kitchen - APC" in warehouses

	entries = frappe.get_all(
		"Stock Entry",
		filters={"pick_list": pick_list.name, "docstatus": 1},
		pluck="name",
	)
	assert len(entries) == 1
	assert (
		frappe.db.get_value("Stock Entry", entries[0], "purpose") == "Material Transfer for Manufacture"
	)

	frappe.db.set_value("BEAM Settings", SETTINGS, "create_stock_entry_on_pick_list_submit", 0)


@pytest.mark.order(28)
def test_get_open_pick_list_for_work_order():
	from beam.beam.pick_list import get_open_pick_list_for_work_order

	work_order = frappe.db.get_value(
		"Work Order", {"production_item": "Pie Crust", "qty": 2, "docstatus": 1}
	)
	pick_list = frappe.db.get_value("Pick List", {"work_order": work_order, "docstatus": 0})
	assert pick_list
	assert get_open_pick_list_for_work_order(work_order) == pick_list


@pytest.mark.order(29)
def test_apply_pick_list_scan_warehouse_gate_and_handling_unit():
	from beam.beam.pick_list import apply_pick_list_scan

	work_order = frappe.db.get_value(
		"Work Order", {"production_item": "Pie Crust", "qty": 2, "docstatus": 1}
	)
	pick_list = frappe.db.get_value("Pick List", {"work_order": work_order, "docstatus": 0})
	refrigerator_barcode = frappe.db.get_value(
		"Item Barcode", {"parenttype": "Warehouse", "parent": "Refrigerator - APC"}, "barcode"
	)
	butter_hu_rows = frappe.get_all(
		"Stock Ledger Entry",
		filters={
			"item_code": "Butter",
			"warehouse": "Refrigerator - APC",
			"handling_unit": ("is", "set"),
		},
		pluck="handling_unit",
		order_by="creation desc",
		limit=1,
	)
	assert refrigerator_barcode
	assert butter_hu_rows
	butter_hu = butter_hu_rows[0]

	gate = apply_pick_list_scan(pick_list, refrigerator_barcode, None)
	assert gate["ok"]
	assert gate["warehouse_gate"] == "Refrigerator - APC"

	pick = apply_pick_list_scan(pick_list, butter_hu, "Refrigerator - APC")
	assert pick["ok"]
	assert flt(pick["picked_qty"]) > 0
	assert pick["item_code"] == "Butter"


def build_staging_pick_list():
	pick_list = frappe.new_doc("Pick List")
	pick_list.company = COMPANY
	pick_list.purpose = "Material Transfer"
	pick_list.scan_mode = 1
	pick_list.append(
		"locations",
		{
			"item_code": "Ambrosia Pie",
			"item_name": "Ambrosia Pie",
			"qty": 1,
			"stock_qty": 1,
			"warehouse": "Baked Goods - APC",
			"uom": "Nos",
			"stock_uom": "Nos",
			"conversion_factor": 1,
			"picked_qty": 1,
		},
	)
	pick_list.save()
	return pick_list


@pytest.mark.order(36)  # after test_demand @31–33: moving Ambrosia Pie splits its allocation
def test_material_transfer_pick_submit_uses_shipping_warehouse():
	"""
	Staging pick list submit moves FG into Shipping when the setting is on.

	| Warehouse         | Stock Ledger |
	| ----------------- | ------------ |
	| Baked Goods - APC | -1 Ambrosia  |
	| Shipping - APC    | +1 Ambrosia  |
	"""
	frappe.db.set_value("BEAM Settings", SETTINGS, "create_stock_entry_on_pick_list_submit", 1)
	frappe.db.set_value("BEAM Settings", SETTINGS, "shipping_warehouse", "Shipping - APC")

	pick_list = build_staging_pick_list()
	baked_before = frappe.db.get_value(
		"Bin", {"item_code": "Ambrosia Pie", "warehouse": "Baked Goods - APC"}, "actual_qty"
	)
	shipping_before = (
		frappe.db.get_value(
			"Bin", {"item_code": "Ambrosia Pie", "warehouse": "Shipping - APC"}, "actual_qty"
		)
		or 0
	)

	pick_list.submit()

	entries = frappe.get_all(
		"Stock Entry",
		filters={"pick_list": pick_list.name, "docstatus": 1},
		pluck="name",
	)
	assert len(entries) == 1
	stock_entry = frappe.get_doc("Stock Entry", entries[0])
	assert stock_entry.purpose == "Material Transfer"
	assert stock_entry.to_warehouse == "Shipping - APC"
	assert stock_entry.items[0].t_warehouse == "Shipping - APC"

	baked_after = frappe.db.get_value(
		"Bin", {"item_code": "Ambrosia Pie", "warehouse": "Baked Goods - APC"}, "actual_qty"
	)
	shipping_after = (
		frappe.db.get_value(
			"Bin", {"item_code": "Ambrosia Pie", "warehouse": "Shipping - APC"}, "actual_qty"
		)
		or 0
	)
	assert flt(baked_after) == flt(baked_before) - 1
	assert flt(shipping_after) == flt(shipping_before) + 1

	frappe.db.set_value("BEAM Settings", SETTINGS, "create_stock_entry_on_pick_list_submit", 0)


@pytest.mark.order(34)
def test_create_stock_entry_on_submit_skips_delivery_purpose():
	from beam.beam.pick_list import create_stock_entry_on_submit

	frappe.db.set_value("BEAM Settings", SETTINGS, "create_stock_entry_on_pick_list_submit", 1)
	before = frappe.db.count("Stock Entry", {"docstatus": 1})
	doc = frappe.get_doc(
		{
			"doctype": "Pick List",
			"company": COMPANY,
			"purpose": "Delivery",
			"docstatus": 1,
			"locations": [
				{
					"item_code": "Ambrosia Pie",
					"qty": 1,
					"stock_qty": 1,
					"warehouse": "Baked Goods - APC",
					"picked_qty": 1,
				}
			],
		}
	)
	create_stock_entry_on_submit(doc)
	after = frappe.db.count("Stock Entry", {"docstatus": 1})
	assert after == before
	frappe.db.set_value("BEAM Settings", SETTINGS, "create_stock_entry_on_pick_list_submit", 0)
