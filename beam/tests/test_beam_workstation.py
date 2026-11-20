# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

pytest_plugins = ["beam.tests.playwright_fixtures"]

import re
import time
import urllib.parse

import frappe
import pytest
from playwright.sync_api import expect

from beam.tests.playwright_utils import (
	goto_beam_portal_route,
	login_playwright,
	use_current_db_transaction,
)
from beam.tests.test_beam_job_card_operation import (
	confirm_pause_with_qty,
	ensure_at_start,
	ensure_operation_running,
	get_operation_elements,
	open_operation_page,
)
from beam.tests.test_beam_scan_to_login import get_user_barcode
from beam.tests.workstation_portal_fixture import (
	BAKE_OP,
	prepare_workstation_portal_story,
	teardown_workstation_portal_story,
)

DEANE_EMAIL = "dsolomon@cfc.co"
OVEN = "Oven Station"
FOOD_PREP = "Food Prep Table 2"
COOLING = "Cooling Racks Station"
PACKAGING = "Packaging Station"


@pytest.fixture(scope="module")
def workstation_portal_story():
	story = prepare_workstation_portal_story()
	yield story
	teardown_workstation_portal_story()


def clear_selected_station(page):
	page.evaluate("() => localStorage.removeItem('beam_selected_workstation')")


def select_station(page, station: str):
	clear_selected_station(page)
	goto_beam_portal_route(page, "/workstation")
	page.get_by_text(station, exact=True).first.click()
	expect(page.get_by_role("heading", name=station)).to_be_visible(timeout=15000)


def set_last_scan_minutes_ago(page, station: str, minutes_ago: float):
	ms = int((time.time() - minutes_ago * 60) * 1000)
	storage_key = f"beam_workstation_scan_{urllib.parse.quote(station, safe='')}"
	page.evaluate(
		"""([storageKey, ts]) => localStorage.setItem(storageKey, String(ts))""",
		[storage_key, ms],
	)
	local_storage_station = "beam_selected_workstation"
	page.evaluate(
		"""([key, name]) => localStorage.setItem(key, name)""",
		[local_storage_station, station],
	)


def queue_labels(page):
	return [line.strip() for line in page.locator(".beam_list-item label").all_inner_texts()]


def open_queue_row(page, text: str):
	row = page.locator(".beam_list-item").filter(has_text=text).first
	expect(row).to_be_visible(timeout=15000)
	row.click()
	expect(page).to_have_url(re.compile(r"#/work_order/"), timeout=15000)


def finish_operation_full_qty(page, work_order: str, operation_id: str, qty: int):
	open_operation_page(page, work_order, operation_id)
	_, _, toggle_button, finish_button = get_operation_elements(page)
	ensure_at_start(page, toggle_button)
	ensure_operation_running(page, toggle_button)
	toggle_button.click()
	confirm_pause_with_qty(page, qty=str(qty))
	expect(finish_button).to_be_enabled(timeout=10000)
	finish_button.click()
	expect(page.locator(".status-text")).to_contain_text(re.compile("Complete", re.I), timeout=15000)


@pytest.mark.order(360)
def test_oven_station_queue_lists_open_bakes(page, workstation_portal_story):
	select_station(page, OVEN)
	labels = queue_labels(page)
	assert any("Bake Op" in label and "Gooseberry" in label for label in labels)
	assert any("Bake Op" in label and "Kaduka" in label for label in labels)
	assert all("Assemble Pie Op" not in label for label in labels)

	page.reload()
	expect(page.get_by_role("heading", name=OVEN)).to_be_visible(timeout=15000)
	labels_after = queue_labels(page)
	assert any("Bake Op" in label for label in labels_after)


@pytest.mark.order(361)
def test_oven_idle_scan_gate(page, workstation_portal_story):
	gooseberry_wo = workstation_portal_story["work_orders"]["Gooseberry Pie"]
	select_station(page, OVEN)
	set_last_scan_minutes_ago(page, OVEN, 1)

	with use_current_db_transaction():
		operation_id = frappe.db.get_value(
			"Job Card", {"work_order": gooseberry_wo, "operation": BAKE_OP}, "operation_id"
		)
	assert operation_id

	open_operation_page(page, gooseberry_wo, operation_id)
	_, _, toggle_button, _ = get_operation_elements(page)
	ensure_at_start(page, toggle_button)
	toggle_button.click()
	expect(toggle_button).to_contain_text("Pause", timeout=15000)

	toggle_button.click()
	confirm_pause_with_qty(page, qty="0")
	expect(toggle_button).to_contain_text("Start", timeout=10000)

	set_last_scan_minutes_ago(page, OVEN, 16)
	toggle_button.click()
	expect(page.get_by_text("Scan your badge", exact=False)).to_be_visible(timeout=10000)

	with use_current_db_transaction():
		butter_barcode = frappe.get_value("Item Barcode", {"parent": "Butter"}, "barcode")
		deane_barcode = get_user_barcode(DEANE_EMAIL)
	assert butter_barcode and deane_barcode

	page.evaluate("barcode => scanner.simulate(window, barcode)", butter_barcode)
	expect(toggle_button).to_contain_text("Start", timeout=10000)

	with page.expect_request(
		lambda request: request.headers.get("x-frappe-cmd") == "beam.beam.scan.user_login.scan_login"
	):
		page.evaluate("barcode => scanner.simulate(window, barcode)", deane_barcode)

	page.wait_for_timeout(1500)
	expect(toggle_button).to_contain_text("Pause", timeout=15000)

	with use_current_db_transaction():
		from beam.beam.manufacturing import persist_open_time_log_closures

		job_card_name = frappe.db.get_value(
			"Job Card", {"work_order": gooseberry_wo, "operation": BAKE_OP}, "name"
		)
		persist_open_time_log_closures(job_card_name)
		jc = frappe.get_doc("Job Card", job_card_name)
		jc.time_logs = []
		jc.total_completed_qty = 0
		jc.status = "Open"
		jc.flags.ignore_permissions = True
		jc.save()
		frappe.db.commit()

	login_playwright(page)


@pytest.mark.order(362)
def test_food_prep_station_has_no_idle_gate(page, workstation_portal_story):
	select_station(page, FOOD_PREP)
	set_last_scan_minutes_ago(page, FOOD_PREP, 120)
	expect(page.get_by_text("Scan your badge", exact=False)).to_have_count(0)
	descriptions = page.locator(".beam_list-item p").all_inner_texts()
	assert not any("Gooseberry Pie" in text and "Assemble" in text for text in descriptions)


@pytest.mark.order(363)
def test_work_order_tablet_columns(page, workstation_portal_story):
	gooseberry_wo = workstation_portal_story["work_orders"]["Gooseberry Pie"]
	select_station(page, OVEN)
	page.set_viewport_size({"width": 1024, "height": 768})
	try:
		open_queue_row(page, "Gooseberry")
		expect(page.get_by_role("heading", name="Materials", exact=True)).to_be_visible(timeout=10000)
		expect(page.get_by_role("heading", name="Operations", exact=True)).to_be_visible(timeout=10000)
		expect(page.get_by_text("Pie Crust", exact=False)).to_be_visible()
		expect(page.get_by_text("Gooseberry Pie Filling", exact=False)).to_be_visible()
		expect(page.get_by_text("Box Pie Op", exact=False)).to_be_visible()
	finally:
		page.set_viewport_size({"width": 480, "height": 854})


@pytest.mark.order(364)
def test_gooseberry_bake_through_manufacture_ledger(page, workstation_portal_story):
	"""
	Bake through manufacture for Gooseberry Pie qty 10.

	| Warehouse           | Stock ledger (qty)                    |
	| ------------------- | ------------------------------------- |
	| Kitchen - APC       | −10 Pie Crust, −40 Gooseberry Filling |
	| Kitchen - APC       | −10 Pie Box                           |
	| Baked Goods - APC   | +10 Gooseberry Pie                    |
	"""
	gooseberry_wo = workstation_portal_story["work_orders"]["Gooseberry Pie"]
	with use_current_db_transaction():
		bake_operation_id = frappe.db.get_value(
			"Job Card", {"work_order": gooseberry_wo, "operation": BAKE_OP}, "operation_id"
		)
		cool_operation_id = frappe.db.get_value(
			"Job Card", {"work_order": gooseberry_wo, "operation": "Cool Pie Op"}, "operation_id"
		)
		box_operation_id = frappe.db.get_value(
			"Job Card", {"work_order": gooseberry_wo, "operation": "Box Pie Op"}, "operation_id"
		)
	assert bake_operation_id and cool_operation_id and box_operation_id

	select_station(page, OVEN)
	set_last_scan_minutes_ago(page, OVEN, 1)
	finish_operation_full_qty(page, gooseberry_wo, bake_operation_id, 10)

	select_station(page, OVEN)
	labels = queue_labels(page)
	assert sum("Bake Op" in label and "Gooseberry" in label for label in labels) == 0
	assert any("Kaduka" in label for label in labels)

	select_station(page, COOLING)
	open_queue_row(page, "Gooseberry")
	finish_operation_full_qty(page, gooseberry_wo, cool_operation_id, 10)

	select_station(page, PACKAGING)
	open_queue_row(page, "Gooseberry")
	finish_operation_full_qty(page, gooseberry_wo, box_operation_id, 10)

	goto_beam_portal_route(page, f"work_order/{gooseberry_wo}")
	expect(page.get_by_text("MANUFACTURE", exact=True)).to_be_visible(timeout=15000)
	set_last_scan_minutes_ago(page, OVEN, 1)
	page.get_by_text("MANUFACTURE", exact=True).click()

	with use_current_db_transaction():
		frappe.db.rollback()
		frappe.db.begin()
		wo = frappe.get_doc("Work Order", gooseberry_wo)
		assert float(wo.produced_qty or 0) == 10
		assert wo.status == "Completed"

		manufacture = frappe.get_all(
			"Stock Entry",
			filters={"work_order": gooseberry_wo, "purpose": "Manufacture", "docstatus": 1},
			pluck="name",
			limit=1,
		)
		assert manufacture, "Expected submitted Manufacture Stock Entry"
		sle = frappe.get_all(
			"Stock Ledger Entry",
			filters={"voucher_no": manufacture[0], "is_cancelled": 0},
			fields=["item_code", "warehouse", "actual_qty"],
		)
		by_item = {(row.item_code, row.warehouse): float(row.actual_qty) for row in sle}
		assert by_item.get(("Pie Crust", "Kitchen - APC")) == -10
		assert by_item.get(("Gooseberry Pie Filling", "Kitchen - APC")) == -40
		assert by_item.get(("Pie Box", "Kitchen - APC")) == -10
		assert by_item.get(("Gooseberry Pie", "Baked Goods - APC")) == 10

		gl = frappe.get_all(
			"GL Entry",
			filters={"voucher_no": manufacture[0], "is_cancelled": 0},
			fields=["account", "debit", "credit"],
		)
		assert gl, "Expected GL Entry rows for Manufacture"


@pytest.mark.order(365)
def test_mixer_station_single_open_operation(page, workstation_portal_story):
	pie_crust_wo = frappe.db.get_value(
		"Work Order",
		{"production_item": "Pie Crust", "qty": 2, "docstatus": 1},
		"name",
		order_by="creation desc",
	)
	if not pie_crust_wo:
		pytest.fail("Expected qty-2 Pie Crust work order from pick demo")

	select_station(page, "Mixer Station")
	labels = queue_labels(page)
	mix_rows = [label for label in labels if "Mix Pie Crust Op" in label]
	assert len(mix_rows) == 1

	open_queue_row(page, "Mix Pie Crust")
	expect(page.get_by_text("Flour", exact=False)).to_be_visible(timeout=15000)
