# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

pytest_plugins = ["beam.tests.playwright_fixtures"]

import re
import time

import frappe
import pytest
from erpnext.manufacturing.doctype.work_order.work_order import create_pick_list
from frappe.utils import flt
from playwright.sync_api import expect

from beam.tests.fixtures import pie_crust_pick_demo
from beam.tests.playwright_utils import (
	error_toast_text,
	goto_beam_portal_route,
	login_beam_portal_user,
	use_current_db_transaction,
	wait_for_docstatus,
)

COMPANY = "Ambrosia Pie Company"


@pytest.fixture(scope="module", autouse=True)
def pick_demos(pie_crust_pick_demo_work_order, delivery_pick_demo_sales_order):
	yield


@pytest.fixture(autouse=True)
def login_as_jordan_mills(page, setup):
	login_beam_portal_user(page, "jmills@cfc.co")
	yield


def draft_pick_list_for(work_order: str) -> str:
	with use_current_db_transaction():
		return frappe.db.get_value("Pick List", {"work_order": work_order, "docstatus": 0})


def open_work_order(page, work_order: str):
	goto_beam_portal_route(page, f"work_order/{work_order}")
	expect(page.get_by_role("heading", name=work_order, exact=True)).to_be_visible(timeout=15000)
	expect(page.get_by_text("View Pick List", exact=True)).to_be_visible(timeout=15000)


def create_isolated_butter_pick_list():
	"""Qty-1 Pie Crust WO + draft pick list (does not touch pie_crust_pick_demo)."""
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
	for row in pie_crust_pick_demo["material_receipts"]:
		receipt.append(
			"items",
			{
				"item_code": row["item_code"],
				"qty": row["qty"],
				"uom": row["uom"],
				"t_warehouse": row["t_warehouse"],
				"basic_rate": row["basic_rate"],
				"expense_account": "5119 - Stock Adjustment - APC",
			},
		)
	receipt.save()
	receipt.submit()

	pick_list = create_pick_list(wo.name, for_qty=1)
	pick_list.scan_mode = 1
	for location in pick_list.locations:
		location.picked_qty = 0
	pick_list.save()
	frappe.db.commit()
	return pick_list.name, wo.name


def warehouse_barcode(warehouse: str) -> str:
	return frappe.db.get_value(
		"Item Barcode", {"parenttype": "Warehouse", "parent": warehouse}, "barcode"
	)


def latest_handling_unit(item_code: str, warehouse: str) -> str | None:
	return frappe.db.get_value(
		"Stock Ledger Entry",
		{
			"item_code": item_code,
			"warehouse": warehouse,
			"handling_unit": ("is", "set"),
		},
		"handling_unit",
		order_by="creation desc",
	)


def item_barcode(item_code: str) -> str:
	barcodes = frappe.get_all(
		"Item Barcode", filters={"parenttype": "Item", "parent": item_code}, pluck="barcode", limit=1
	)
	assert barcodes
	return barcodes[0]


def simulate_scan(page, barcode: str) -> None:
	assert barcode, "No barcode to scan"
	page.evaluate("barcode => scanner.simulate(window, barcode)", barcode)
	page.wait_for_timeout(500)


def line_is_full(count_loc) -> bool:
	match = re.match(r"([\d.]+)/([\d.]+)", count_loc.inner_text().strip())
	if not match:
		return False
	return flt(match.group(1)) >= flt(match.group(2))


def expect_line_fully_picked(page, count_loc, label: str, timeout_ms: float = 15000) -> None:
	deadline = time.monotonic() + timeout_ms / 1000
	while time.monotonic() < deadline:
		if line_is_full(count_loc):
			return
		time.sleep(0.15)
	raise AssertionError(
		f"{label} stuck at {count_loc.inner_text().strip()!r}; toast: {error_toast_text(page)!r}"
	)


def pick_all_lines_via_scan(page, pick_list_name: str) -> None:
	"""Scan every pick line in sort order. Progress lives in Pinia until SAVE, not MariaDB."""
	with use_current_db_transaction():
		doc = frappe.get_doc("Pick List", pick_list_name)
		rows = sorted(doc.locations, key=lambda row: (row.warehouse or "", row.item_code or ""))

	for row in rows:
		target = flt(row.stock_qty) or flt(row.qty)
		item_code = row.item_code
		warehouse = row.warehouse
		line = page.locator(".beam_list-item").filter(has_text=item_code).first
		count_loc = line.locator(".beam_item-count")
		hu = latest_handling_unit(item_code, warehouse)
		use_hu = bool(frappe.db.get_value("Item", item_code, "enable_handling_unit") and hu)

		label = f"{item_code} @ {warehouse}"

		simulate_scan(page, warehouse_barcode(warehouse))
		if use_hu:
			assert hu
			simulate_scan(page, hu)
		else:
			for _ in range(int(target) + 1):
				if line_is_full(count_loc):
					break
				simulate_scan(page, item_barcode(item_code))
		expect_line_fully_picked(page, count_loc, label)


@pytest.mark.order(314)
def test_work_order_with_pick_list_shows_view_pick_list_not_transfer(
	page, pie_crust_pick_demo_work_order
):
	open_work_order(page, pie_crust_pick_demo_work_order)
	expect(page.get_by_text("TRANSFER", exact=True)).to_have_count(0)
	page.get_by_text("View Pick List", exact=True).click()
	expect(page).to_have_url(re.compile(r"pick-list/"), timeout=15000)


@pytest.mark.order(315)
def test_pick_list_warehouse_gate_and_butter_scan(page, pie_crust_pick_demo_work_order):
	pick_list = draft_pick_list_for(pie_crust_pick_demo_work_order)
	open_work_order(page, pie_crust_pick_demo_work_order)
	page.get_by_text("View Pick List", exact=True).click()
	expect(page).to_have_url(re.compile(rf"pick-list/{re.escape(pick_list)}"), timeout=15000)

	with use_current_db_transaction():
		refrigerator_barcode = frappe.db.get_value(
			"Item Barcode", {"parenttype": "Warehouse", "parent": "Refrigerator - APC"}, "barcode"
		)
		butter_hu = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "Butter", "warehouse": "Refrigerator - APC", "handling_unit": ("is", "set")},
			"handling_unit",
			order_by="creation desc",
		)
		flour_hu = frappe.db.get_value(
			"Stock Ledger Entry",
			{"item_code": "Flour", "warehouse": "Refrigerator - APC", "handling_unit": ("is", "set")},
			"handling_unit",
			order_by="creation desc",
		)

	assert refrigerator_barcode
	assert butter_hu

	page.evaluate("barcode => scanner.simulate(window, barcode)", refrigerator_barcode)
	page.wait_for_timeout(500)

	if flour_hu:
		page.evaluate("barcode => scanner.simulate(window, barcode)", flour_hu)
		page.wait_for_timeout(500)

	butter_line = page.locator(".beam_list-item").filter(has_text="Butter").first
	butter_count = butter_line.locator(".beam_item-count")
	expect(butter_count).to_have_text(re.compile(r"0/"))

	page.evaluate("barcode => scanner.simulate(window, barcode)", refrigerator_barcode)
	page.wait_for_timeout(500)
	page.evaluate("barcode => scanner.simulate(window, barcode)", butter_hu)
	page.wait_for_timeout(500)
	expect(butter_count).not_to_have_text(re.compile(r"^0/"))

	with use_current_db_transaction():
		for row in frappe.get_all(
			"Pick List Item",
			filters={"parent": pick_list, "item_code": "Butter"},
			pluck="name",
		):
			frappe.db.set_value("Pick List Item", row, "picked_qty", 0)


@pytest.mark.order(316)
def test_butter_pick_list_scan_save_submit(page):
	"""
	Isolated qty-1 Pie Crust pick list: scan all lines, SAVE, SUBMIT (setting off).

	Does not consume pie_crust_pick_demo (qty-2) draft used by tests 314–315.
	"""
	frappe.db.set_value("BEAM Settings", COMPANY, "create_stock_entry_on_pick_list_submit", 0)
	frappe.db.commit()

	pick_list_name, work_order = create_isolated_butter_pick_list()
	with use_current_db_transaction():
		location_count = frappe.db.count("Pick List Item", {"parent": pick_list_name})

	goto_beam_portal_route(page, f"/pick-list/{pick_list_name}")
	expect(page.get_by_role("heading", name="Pick List", exact=True)).to_be_visible(timeout=15000)

	pick_all_lines_via_scan(page, pick_list_name)

	submit_button = page.get_by_role("button", name="SUBMIT", exact=True)
	expect(submit_button).to_be_enabled(timeout=15000)

	save_button = page.get_by_role("button", name="SAVE", exact=True)
	expect(save_button).to_be_enabled(timeout=15000)
	save_button.click()
	expect(page.get_by_text("Unsaved", exact=True)).to_have_count(0, timeout=15000)

	with use_current_db_transaction():
		for row in frappe.get_all(
			"Pick List Item",
			filters={"parent": pick_list_name},
			fields=["item_code", "picked_qty", "stock_qty"],
		):
			assert flt(row.picked_qty) >= flt(row.stock_qty)

	submit_button.click()
	wait_for_docstatus("Pick List", pick_list_name, 1)

	with use_current_db_transaction():
		assert not frappe.db.exists("Stock Entry", {"pick_list": pick_list_name, "docstatus": 1})
		butter_line = frappe.get_all(
			"Pick List Item",
			filters={"parent": pick_list_name, "item_code": "Butter"},
			fields=["picked_qty", "stock_qty"],
		)
		assert butter_line
		assert flt(butter_line[0].picked_qty) >= flt(butter_line[0].stock_qty)
		assert location_count >= 1
		assert work_order


@pytest.mark.order(317)
def test_pick_queue_lists_open_pick_lists(page):
	goto_beam_portal_route(page, "/pick-list")
	expect(page.get_by_role("heading", name="Pick", exact=True)).to_be_visible(timeout=15000)

	with use_current_db_transaction():
		draft_names = frappe.get_all(
			"Pick List",
			filters={"docstatus": 0, "status": ["!=", "Cancelled"]},
			pluck="name",
			limit=5,
		)
	assert draft_names
	for name in draft_names[:2]:
		expect(page.get_by_text(name, exact=True)).to_be_visible(timeout=15000)


@pytest.mark.order(318)
def test_delivery_pick_list_opens_from_queue(page, delivery_pick_demo_sales_order):
	with use_current_db_transaction():
		delivery_pick = frappe.db.get_value(
			"Pick List Item",
			{"sales_order": delivery_pick_demo_sales_order, "parenttype": "Pick List", "docstatus": 0},
			"parent",
		)
	assert delivery_pick

	goto_beam_portal_route(page, "/pick-list")
	page.get_by_text(delivery_pick, exact=True).click()
	expect(page).to_have_url(re.compile(rf"pick-list/{re.escape(delivery_pick)}"), timeout=15000)
	expect(page.get_by_role("heading", name="Pick List", exact=True)).to_be_visible()
	expect(page.get_by_text("Ambrosia Pie", exact=False)).to_be_visible()
	expect(page.get_by_text("Double Plum Pie", exact=False)).to_be_visible()


@pytest.mark.order(319)
def test_work_order_with_pick_list_shows_read_only_material_counts(
	page, pie_crust_pick_demo_work_order
):
	open_work_order(page, pie_crust_pick_demo_work_order)

	butter_line = page.locator(".box .beam_list-item").filter(has_text="Butter").first
	expect(butter_line.locator(".beam_item-count")).to_be_visible()
	expect(page.get_by_text("TRANSFER", exact=True)).to_have_count(0)
