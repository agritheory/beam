# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest

from beam.beam.inventory_dimension import (
	propagate_inventory_dimensions,
	setup_inventory_dimensions,
)
from beam.beam.scan import clear_inv_dim_cache, get_inv_dim_source_fieldnames


# --- Inventory Dimension cache -----------------------------------------------


def test_inv_dim_cache_returns_list():
	clear_inv_dim_cache()
	result = get_inv_dim_source_fieldnames()
	assert isinstance(result, list)


def test_inv_dim_cache_excludes_handling_unit():
	clear_inv_dim_cache()
	result = get_inv_dim_source_fieldnames()
	assert "handling_unit" not in result


def test_inv_dim_cache_invalidation_refetches():
	result_before = get_inv_dim_source_fieldnames()
	clear_inv_dim_cache()
	result_after = get_inv_dim_source_fieldnames()
	assert result_before == result_after


# --- setup_inventory_dimensions ----------------------------------------------


def test_setup_skips_existing_dimension():
	"""Calling setup for an already-existing dimension should be a no-op."""
	assert frappe.db.exists("Inventory Dimension", "Handling Unit")
	setup_inventory_dimensions(
		[{"dimension_name": "Handling Unit", "reference_document": "Handling Unit"}]
	)
	assert frappe.db.exists("Inventory Dimension", "Handling Unit")


def test_setup_applies_default_apply_to_all(monkeypatch):
	"""When apply_to_all_doctypes is not specified, setup should default it to 1 in the input dict."""
	input_dict = {"dimension_name": "__Test Beam Dim", "reference_document": "Supplier"}

	class FakeInvDim:
		def update(self, d):
			pass

		def save(self):
			raise RuntimeError("stop before persistence")

	monkeypatch.setattr("frappe.new_doc", lambda _dt: FakeInvDim())
	try:
		setup_inventory_dimensions([input_dict])
	except RuntimeError:
		pass
	assert input_dict.get("apply_to_all_doctypes") == 1


# --- propagate_inventory_dimensions ------------------------------------------


def submit_all_purchase_receipts():
	for pi in frappe.get_all("Purchase Invoice", {"docstatus": 0}):
		frappe.get_doc("Purchase Invoice", pi).submit()
	for pr in frappe.get_all("Purchase Receipt", {"docstatus": 0}):
		frappe.get_doc("Purchase Receipt", pr).submit()


def test_propagate_skips_rows_without_both_warehouses():
	"""Rows missing s_warehouse or t_warehouse should not be touched."""
	company = frappe.defaults.get_defaults().get("company")
	beam_settings = frappe.get_doc("BEAM Settings", {"company": company})
	if not beam_settings.enable_handling_units:
		pytest.skip("Handling units not enabled")

	original = frappe.db.get_value("Inventory Dimension", "Handling Unit", "custom_carry_forward")
	try:
		frappe.db.set_value("Inventory Dimension", "Handling Unit", "custom_carry_forward", 1)
		clear_inv_dim_cache()

		doc = frappe.new_doc("Stock Entry")
		doc.append(
			"items",
			{
				"item_code": "Ambrosia Pie",
				"s_warehouse": "Baked Goods - APC",
				"t_warehouse": None,
				"handling_unit": "HU-TEST-1",
				"to_handling_unit": None,
			},
		)
		doc.append(
			"items",
			{
				"item_code": "Ambrosia Pie",
				"s_warehouse": None,
				"t_warehouse": "Kitchen - APC",
				"handling_unit": "HU-TEST-2",
				"to_handling_unit": None,
			},
		)
		propagate_inventory_dimensions(doc)
		assert not doc.items[0].to_handling_unit
		assert not doc.items[1].to_handling_unit
	finally:
		frappe.db.set_value(
			"Inventory Dimension", "Handling Unit", "custom_carry_forward", original or 0
		)
		clear_inv_dim_cache()


def test_propagate_copies_source_to_empty_target():
	"""When carry_forward is on and target is empty, source should be copied to target."""
	company = frappe.defaults.get_defaults().get("company")
	beam_settings = frappe.get_doc("BEAM Settings", {"company": company})
	if not beam_settings.enable_handling_units:
		pytest.skip("Handling units not enabled")

	original_cf = frappe.db.get_value("Inventory Dimension", "Handling Unit", "custom_carry_forward")
	try:
		frappe.db.set_value("Inventory Dimension", "Handling Unit", "custom_carry_forward", 1)
		clear_inv_dim_cache()

		doc = frappe.new_doc("Stock Entry")
		doc.append(
			"items",
			{
				"item_code": "Ambrosia Pie",
				"s_warehouse": "Baked Goods - APC",
				"t_warehouse": "Kitchen - APC",
				"handling_unit": "HU-TEST-CF",
				"to_handling_unit": None,
			},
		)
		propagate_inventory_dimensions(doc)
		assert doc.items[0].to_handling_unit == "HU-TEST-CF"
	finally:
		frappe.db.set_value(
			"Inventory Dimension", "Handling Unit", "custom_carry_forward", original_cf or 0
		)
		clear_inv_dim_cache()


def test_propagate_does_not_overwrite_existing_target():
	"""When target is already set, it should not be overwritten."""
	company = frappe.defaults.get_defaults().get("company")
	beam_settings = frappe.get_doc("BEAM Settings", {"company": company})
	if not beam_settings.enable_handling_units:
		pytest.skip("Handling units not enabled")

	original = frappe.db.get_value("Inventory Dimension", "Handling Unit", "custom_carry_forward")
	try:
		frappe.db.set_value("Inventory Dimension", "Handling Unit", "custom_carry_forward", 1)
		clear_inv_dim_cache()

		doc = frappe.new_doc("Stock Entry")
		doc.append(
			"items",
			{
				"item_code": "Ambrosia Pie",
				"s_warehouse": "Baked Goods - APC",
				"t_warehouse": "Kitchen - APC",
				"handling_unit": "HU-SOURCE",
				"to_handling_unit": "HU-EXISTING-TARGET",
			},
		)
		propagate_inventory_dimensions(doc)
		assert doc.items[0].to_handling_unit == "HU-EXISTING-TARGET"
	finally:
		frappe.db.set_value(
			"Inventory Dimension", "Handling Unit", "custom_carry_forward", original or 0
		)
		clear_inv_dim_cache()


def test_propagate_skips_dim_without_carry_forward():
	"""Dimensions with carry_forward off should not propagate."""
	original = frappe.db.get_value("Inventory Dimension", "Handling Unit", "custom_carry_forward")
	try:
		frappe.db.set_value("Inventory Dimension", "Handling Unit", "custom_carry_forward", 0)
		clear_inv_dim_cache()

		doc = frappe.new_doc("Stock Entry")
		doc.append(
			"items",
			{
				"item_code": "Ambrosia Pie",
				"s_warehouse": "Baked Goods - APC",
				"t_warehouse": "Kitchen - APC",
				"handling_unit": "HU-TEST-NOCF",
				"to_handling_unit": None,
			},
		)
		propagate_inventory_dimensions(doc)
		assert not doc.items[0].to_handling_unit
	finally:
		frappe.db.set_value(
			"Inventory Dimension", "Handling Unit", "custom_carry_forward", original or 0
		)
		clear_inv_dim_cache()


def test_propagate_skips_rows_without_item_code():
	"""Rows without item_code (blank starter rows) should be skipped."""
	original = frappe.db.get_value("Inventory Dimension", "Handling Unit", "custom_carry_forward")
	try:
		frappe.db.set_value("Inventory Dimension", "Handling Unit", "custom_carry_forward", 1)
		clear_inv_dim_cache()

		doc = frappe.new_doc("Stock Entry")
		doc.append(
			"items",
			{
				"item_code": None,
				"s_warehouse": "Baked Goods - APC",
				"t_warehouse": "Kitchen - APC",
				"handling_unit": "HU-BLANK",
				"to_handling_unit": None,
			},
		)
		propagate_inventory_dimensions(doc)
		assert not doc.items[0].to_handling_unit
	finally:
		frappe.db.set_value(
			"Inventory Dimension", "Handling Unit", "custom_carry_forward", original or 0
		)
		clear_inv_dim_cache()


# --- HU carry-forward integration tests --------------------------------------
#
# With carry_forward enabled, propagate_inventory_dimensions copies handling_unit →
# to_handling_unit before BEAM's generate_handling_units runs. BEAM now respects a
# pre-filled to_handling_unit and skips creating a new one, preserving the HU label
# across warehouse transfers (the HU is a physical sticker, not a container that changes).


@pytest.mark.order(after="test_stock_entry_material_receipt")
def test_hu_carry_forward_partial_transfer_creates_new_hu():
	"""Partial qty transfer with carry_forward: propagate copies source → target, but
	BEAM detects qty mismatch and overrides with a new HU (physical split)."""
	submit_all_purchase_receipts()

	se_receipt = frappe.new_doc("Stock Entry")
	se_receipt.stock_entry_type = se_receipt.purpose = "Material Receipt"
	se_receipt.append(
		"items",
		{
			"item_code": "Ambrosia Pie",
			"qty": 50,
			"t_warehouse": "Baked Goods - APC",
			"basic_rate": frappe.get_value("Item Price", {"item_code": "Ambrosia Pie"}, "price_list_rate"),
		},
	)
	se_receipt.save()
	se_receipt.submit()
	source_hu = se_receipt.items[0].handling_unit
	assert source_hu

	original = frappe.db.get_value("Inventory Dimension", "Handling Unit", "custom_carry_forward")
	try:
		frappe.db.set_value("Inventory Dimension", "Handling Unit", "custom_carry_forward", 1)
		clear_inv_dim_cache()

		se_transfer = frappe.new_doc("Stock Entry")
		se_transfer.stock_entry_type = se_transfer.purpose = "Material Transfer"
		se_transfer.company = frappe.defaults.get_defaults().get("company")
		se_transfer.append(
			"items",
			{
				"item_code": "Ambrosia Pie",
				"qty": 20,
				"transfer_qty": 20,
				"s_warehouse": "Baked Goods - APC",
				"t_warehouse": "Kitchen - APC",
				"handling_unit": source_hu,
				"basic_rate": frappe.get_value("Item Price", {"item_code": "Ambrosia Pie"}, "price_list_rate"),
			},
		)
		se_transfer.save()
		se_transfer.submit()

		row = se_transfer.items[0]
		# qty 20 != HU stock 50 → BEAM overrides carry-forward with new HU
		assert row.to_handling_unit
		assert row.to_handling_unit != source_hu

		from beam.beam.scan import get_handling_unit

		# Source HU retains remainder
		hu_source = get_handling_unit(source_hu)
		assert hu_source.stock_qty == 30

		# New HU has split portion
		hu_target = get_handling_unit(row.to_handling_unit)
		assert hu_target.stock_qty == 20

	finally:
		frappe.db.set_value(
			"Inventory Dimension", "Handling Unit", "custom_carry_forward", original or 0
		)
		clear_inv_dim_cache()


@pytest.mark.order(after="test_stock_entry_material_receipt")
def test_hu_carry_forward_full_transfer_conserves_hu():
	"""Full qty transfer: HU label follows the stock to the new warehouse."""
	submit_all_purchase_receipts()

	se_receipt = frappe.new_doc("Stock Entry")
	se_receipt.stock_entry_type = se_receipt.purpose = "Material Receipt"
	se_receipt.append(
		"items",
		{
			"item_code": "Ambrosia Pie",
			"qty": 25,
			"t_warehouse": "Baked Goods - APC",
			"basic_rate": frappe.get_value("Item Price", {"item_code": "Ambrosia Pie"}, "price_list_rate"),
		},
	)
	se_receipt.save()
	se_receipt.submit()
	source_hu = se_receipt.items[0].handling_unit

	original_cf = frappe.db.get_value("Inventory Dimension", "Handling Unit", "custom_carry_forward")
	try:
		frappe.db.set_value("Inventory Dimension", "Handling Unit", "custom_carry_forward", 1)
		clear_inv_dim_cache()

		se_transfer = frappe.new_doc("Stock Entry")
		se_transfer.stock_entry_type = se_transfer.purpose = "Material Transfer"
		se_transfer.company = frappe.defaults.get_defaults().get("company")
		se_transfer.append(
			"items",
			{
				"item_code": "Ambrosia Pie",
				"qty": 25,
				"transfer_qty": 25,
				"s_warehouse": "Baked Goods - APC",
				"t_warehouse": "Kitchen - APC",
				"handling_unit": source_hu,
				"basic_rate": frappe.get_value("Item Price", {"item_code": "Ambrosia Pie"}, "price_list_rate"),
			},
		)
		se_transfer.save()
		se_transfer.submit()

		row = se_transfer.items[0]
		# Same HU carried forward
		assert row.to_handling_unit == source_hu

		from beam.beam.scan import get_handling_unit

		# HU retains the transferred qty
		hu = get_handling_unit(source_hu)
		assert hu.stock_qty == 25

	finally:
		frappe.db.set_value(
			"Inventory Dimension", "Handling Unit", "custom_carry_forward", original_cf or 0
		)
		clear_inv_dim_cache()


@pytest.mark.order(after="test_stock_entry_material_receipt")
def test_hu_carry_forward_off_creates_new_hu():
	"""Without carry_forward, BEAM's default behavior creates a new to_handling_unit."""
	submit_all_purchase_receipts()

	se_receipt = frappe.new_doc("Stock Entry")
	se_receipt.stock_entry_type = se_receipt.purpose = "Material Receipt"
	se_receipt.append(
		"items",
		{
			"item_code": "Ambrosia Pie",
			"qty": 30,
			"t_warehouse": "Baked Goods - APC",
			"basic_rate": frappe.get_value("Item Price", {"item_code": "Ambrosia Pie"}, "price_list_rate"),
		},
	)
	se_receipt.save()
	se_receipt.submit()
	source_hu = se_receipt.items[0].handling_unit

	original = frappe.db.get_value("Inventory Dimension", "Handling Unit", "custom_carry_forward")
	try:
		frappe.db.set_value("Inventory Dimension", "Handling Unit", "custom_carry_forward", 0)
		clear_inv_dim_cache()

		se_transfer = frappe.new_doc("Stock Entry")
		se_transfer.stock_entry_type = se_transfer.purpose = "Material Transfer"
		se_transfer.company = frappe.defaults.get_defaults().get("company")
		se_transfer.append(
			"items",
			{
				"item_code": "Ambrosia Pie",
				"qty": 10,
				"transfer_qty": 10,
				"s_warehouse": "Baked Goods - APC",
				"t_warehouse": "Kitchen - APC",
				"handling_unit": source_hu,
				"basic_rate": frappe.get_value("Item Price", {"item_code": "Ambrosia Pie"}, "price_list_rate"),
			},
		)
		se_transfer.save()
		se_transfer.submit()

		row = se_transfer.items[0]
		# Default BEAM: new HU on target
		assert row.to_handling_unit
		assert row.to_handling_unit != source_hu

	finally:
		frappe.db.set_value(
			"Inventory Dimension", "Handling Unit", "custom_carry_forward", original or 0
		)
		clear_inv_dim_cache()
