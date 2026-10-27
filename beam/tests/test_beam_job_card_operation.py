# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

pytest_plugins = ["beam.tests.playwright_fixtures"]

import re

import frappe
import pytest
from playwright.sync_api import Page, expect

from beam.tests.manufacturing_test_utils import pause_open_job_cards_for_user
from beam.tests.playwright_utils import (
	goto_beam_portal_route,
	login_beam_portal_user,
	open_first_beam_list_row,
	use_current_db_transaction,
)

# NOTE: any navigation tests should be done using `expect(page).to_have_url` since
# `page.expect_navigation()` won't work with Beam's hash-based routes


@pytest.fixture(autouse=True)
def login_as_jordan_mills(page, setup):
	login_beam_portal_user(page, "jmills@cfc.co")
	yield


@pytest.fixture(autouse=True)
def jordan_has_no_active_job_card():
	pause_open_job_cards_for_user("jmills@cfc.co")
	frappe.db.commit()
	yield


def open_first_operation_id_from_manufacture(page) -> str:
	"""Navigate Home -> Manufacture -> Work Order -> first Operation."""
	open_first_beam_list_row(page, "Manufacture", r"work_order/")

	operation_link = page.locator("a[href*='/operation/']").first
	expect(operation_link).to_be_visible(timeout=15000)
	operation_link.click()
	expect(page).to_have_url(re.compile(r"#/work_order/[^/]+/operation/[^/?#]+"), timeout=15000)

	match = re.search(r"#/work_order/([^/]+)/operation/([^/?#]+)", page.url)
	assert match, f"Could not parse operation route from URL: {page.url}"
	return match.group(2)


def open_operation_page(page: Page, work_order: str, operation_id: str) -> None:
	goto_beam_portal_route(page, f"work_order/{work_order}/operation/{operation_id}")
	expect(page.locator(".operation-title")).to_be_visible(timeout=15000)


def hms_to_seconds(value: str) -> int:
	hours, minutes, seconds = (int(part) for part in value.split(":"))
	return (hours * 3600) + (minutes * 60) + seconds


def get_operation_elements(page):
	description_box = page.locator("css=.metadata-box").first
	timer_text = page.locator("css=.timer-value").first
	toggle_button = page.locator(".actions button").first
	finish_button = page.get_by_role("button", name="Finish")
	return description_box, timer_text, toggle_button, finish_button


def confirm_pause_with_qty(page, qty: str = "0"):
	qty_input = page.locator(".qty-input-row input").first
	expect(qty_input).to_be_visible(timeout=10000)
	qty_input.click()
	qty_input.press("Control+a")
	qty_input.press_sequentially(qty, delay=80)
	expect(qty_input).to_have_value(qty, timeout=5000)
	page.get_by_role("button", name="Confirm").click()


def pause_form_is_visible(page) -> bool:
	return page.locator(".qty-input-row input").first.is_visible()


def assert_start_rejected_without_wip(page, toggle_button, job_card_name: str) -> None:
	with use_current_db_transaction():
		before = frappe.get_all("Job Card Time Log", filters={"parent": job_card_name}, pluck="name")

	toggle_button.click()
	expect(page.locator(".action-error")).to_contain_text("Failed to start job card", timeout=10000)
	expect(toggle_button).to_contain_text("Start", timeout=10000)

	with use_current_db_transaction():
		after = frappe.get_all("Job Card Time Log", filters={"parent": job_card_name}, pluck="name")

	assert after == before, "Start wrote a time log before materials were in WIP"


def expected_toggle_label(job_card_name: str) -> str:
	"""An open time log means the operation is running, unless the job card is On Hold."""
	if frappe.get_value("Job Card", job_card_name, "status") == "On Hold":
		return "Start"
	last_log = frappe.get_all(
		"Job Card Time Log",
		filters={"parent": job_card_name},
		fields=["from_time", "to_time"],
		order_by="creation desc",
		limit=1,
	)
	if last_log and last_log[0].from_time and not last_log[0].to_time:
		return "Pause"
	return "Start"


def ensure_at_start(page, toggle_button):
	label = toggle_button.inner_text().strip()
	if label == "Start":
		return
	if label == "Pause":
		toggle_button.click()
		confirm_pause_with_qty(page)
		expect(toggle_button).to_contain_text("Start", timeout=10000)
		return
	pytest.fail(f"Unexpected toggle label: {label}")


def ensure_operation_running(page, toggle_button):
	current_label = toggle_button.inner_text().strip()
	if current_label == "Pause":
		return
	if current_label != "Start":
		pytest.fail(f"Unexpected toggle label before start: {current_label}")

	toggle_button.click()
	if pause_form_is_visible(page):
		confirm_pause_with_qty(page)
		expect(toggle_button).to_contain_text("Start", timeout=10000)
		toggle_button.click()

	expect(toggle_button).to_contain_text("Pause", timeout=10000)


@pytest.mark.order(355)
def test_operation_details_are_visible(page):
	operation_id = open_first_operation_id_from_manufacture(page)
	description_box, timer_text, toggle_button, finish_button = get_operation_elements(page)

	expect(description_box).to_be_visible(timeout=15000)
	expect(timer_text).to_be_visible(timeout=15000)
	expect(toggle_button).to_be_visible(timeout=15000)
	expect(finish_button).to_be_visible(timeout=15000)
	expect(toggle_button).to_contain_text(re.compile("Start|Pause"), timeout=15000)

	with use_current_db_transaction():
		operation = frappe.get_value(
			"Work Order Operation",
			operation_id,
			["name", "description"],
			as_dict=True,
		)

	assert operation, f"Operation {operation_id} not found"

	if operation.description:
		expect(description_box).to_contain_text(operation.description)

	elapsed = timer_text.inner_text().strip()
	assert re.fullmatch(r"\d{2}:\d{2}:\d{2}", elapsed), f"Unexpected elapsed time format: {elapsed}"


@pytest.mark.order(356)
def test_start_rejected_without_wip_material(page, pie_crust_pick_demo_work_order):
	with use_current_db_transaction():
		operation_id = frappe.db.get_value(
			"Job Card",
			{"work_order": pie_crust_pick_demo_work_order},
			"operation_id",
			order_by="sequence_id asc",
		)
		job_card_name = frappe.db.get_value("Job Card", {"operation_id": operation_id}, "name")
		transferred = frappe.db.get_value(
			"Work Order", pie_crust_pick_demo_work_order, "material_transferred_for_manufacturing"
		)

	assert operation_id and job_card_name
	assert float(transferred or 0) <= 0

	open_operation_page(page, pie_crust_pick_demo_work_order, operation_id)
	_, _, toggle_button, finish_button = get_operation_elements(page)
	expect(toggle_button).to_contain_text("Start", timeout=15000)
	expect(toggle_button).to_be_enabled(timeout=15000)
	expect(finish_button).to_be_disabled()
	assert_start_rejected_without_wip(page, toggle_button, job_card_name)


@pytest.mark.order(357)
def test_start_operation_starts_timer_and_toggles_buttons(page, job_card_operation_with_wip):
	operation_id = job_card_operation_with_wip["operation_id"]
	open_operation_page(page, job_card_operation_with_wip["work_order"], operation_id)
	_, timer_text, toggle_button, finish_button = get_operation_elements(page)

	expect(toggle_button).to_be_enabled(timeout=15000)
	with use_current_db_transaction():
		job_card = frappe.get_value(
			"Job Card",
			{"operation_id": operation_id},
			["name", "status", "for_quantity", "total_completed_qty"],
			as_dict=True,
		)

	assert job_card and job_card.get(
		"name"
	), f"Expected a Job Card linked to operation {operation_id}"

	page.wait_for_timeout(1000)
	with use_current_db_transaction():
		expected_label = expected_toggle_label(job_card.get("name"))
	label = toggle_button.inner_text().strip()
	expect(toggle_button).to_contain_text(expected_label, timeout=15000)
	ensure_at_start(page, toggle_button)
	expect(finish_button).to_be_disabled()

	initial_elapsed = timer_text.inner_text().strip()
	assert re.fullmatch(r"\d{2}:\d{2}:\d{2}", initial_elapsed)

	toggle_button.click()
	expect(toggle_button).to_be_enabled(timeout=10000)
	expect(toggle_button).to_contain_text("Pause", timeout=10000)
	expect(finish_button).to_be_disabled()

	page.wait_for_timeout(1500)
	updated_elapsed = timer_text.inner_text().strip()
	assert re.fullmatch(r"\d{2}:\d{2}:\d{2}", updated_elapsed)
	assert hms_to_seconds(updated_elapsed) > hms_to_seconds(initial_elapsed)


@pytest.mark.order(358)
def test_stop_operation_stops_timer_and_records_time_log(page, job_card_operation_with_wip):
	operation_id = job_card_operation_with_wip["operation_id"]
	open_operation_page(page, job_card_operation_with_wip["work_order"], operation_id)
	_, timer_text, toggle_button, finish_button = get_operation_elements(page)

	with use_current_db_transaction():
		job_card_name = frappe.get_value("Job Card", {"operation_id": operation_id}, "name")
		initial_logs = frappe.get_all(
			"Job Card Time Log",
			filters={"parent": job_card_name},
			fields=["name", "from_time", "to_time", "time_in_mins", "completed_qty"],
		)

	assert job_card_name, f"Expected a Job Card linked to operation {operation_id}"
	initial_closed_logs = len([log for log in initial_logs if log.to_time])

	ensure_at_start(page, toggle_button)
	expect(finish_button).to_be_disabled()
	ensure_operation_running(page, toggle_button)
	expect(finish_button).to_be_disabled()

	page.wait_for_timeout(1200)
	timer_after_start = timer_text.inner_text().strip()

	pause_qty = "0"
	toggle_button.click()
	confirm_pause_with_qty(page, qty=pause_qty)
	expect(toggle_button).to_contain_text("Start", timeout=10000)
	expect(finish_button).to_be_disabled()

	page.wait_for_timeout(1500)
	timer_after_stop = timer_text.inner_text().strip()
	page.wait_for_timeout(1200)
	timer_after_wait = timer_text.inner_text().strip()

	assert timer_after_stop == timer_after_wait

	start_sec = hms_to_seconds(timer_after_start)
	stop_sec = hms_to_seconds(timer_after_stop)
	assert (
		stop_sec >= start_sec - 1
	), f"Timer decreased unexpectedly: {timer_after_start} -> {timer_after_stop}"

	with use_current_db_transaction():
		final_logs = frappe.get_all(
			"Job Card Time Log",
			filters={"parent": job_card_name},
			fields=["name", "from_time", "to_time", "time_in_mins", "completed_qty"],
			order_by="creation desc",
		)

	final_closed_logs = len([log for log in final_logs if log.to_time])
	assert final_closed_logs >= initial_closed_logs + 1
	newest_closed = next(log for log in final_logs if log.to_time)
	assert newest_closed.time_in_mins and newest_closed.time_in_mins > 0
	assert float(newest_closed.completed_qty or 0) == float(pause_qty)


@pytest.mark.order(359)
def test_finish_operation_submits_job_card(page, job_card_operation_with_wip):
	operation_id = job_card_operation_with_wip["operation_id"]
	open_operation_page(page, job_card_operation_with_wip["work_order"], operation_id)
	_, _, toggle_button, finish_button = get_operation_elements(page)

	with use_current_db_transaction():
		job_card_name = frappe.get_value("Job Card", {"operation_id": operation_id}, "name")
		for_quantity = frappe.get_value("Job Card", job_card_name, "for_quantity")

	assert job_card_name

	ensure_at_start(page, toggle_button)
	ensure_operation_running(page, toggle_button)
	toggle_button.click()
	confirm_pause_with_qty(page, qty=str(int(for_quantity)))
	expect(finish_button).to_be_visible(timeout=10000)
	expect(finish_button).to_be_enabled(timeout=10000)

	finish_button.click()
	expect(page.locator(".status-text")).to_contain_text(re.compile("Complete", re.I), timeout=15000)

	with use_current_db_transaction():
		job_card = frappe.get_doc("Job Card", job_card_name)
		logs = frappe.get_all(
			"Job Card Time Log",
			filters={"parent": job_card_name},
			fields=["to_time"],
		)

	assert job_card.docstatus == 1
	assert float(job_card.total_completed_qty or 0) == float(for_quantity)
	open_logs = [log for log in logs if not log.to_time]
	assert not open_logs, f"Expected every time log closed after Finish, found open: {open_logs}"
