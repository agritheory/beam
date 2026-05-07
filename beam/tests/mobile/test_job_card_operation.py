# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import re

import frappe
import pytest
from playwright.sync_api import expect

from beam.tests.test_utils import use_current_db_transaction

# NOTE: any navigation tests should be done using `expect(page).to_have_url` since
# `page.expect_navigation()` won't work with Beam's hash-based routes


@pytest.fixture(autouse=True)
def login_as_jordan_mills(page):
	base_url = frappe.utils.get_url()
	page.context.clear_cookies()
	page.goto(base_url)
	email_field = page.get_by_role("textbox", name="Email")
	expect(email_field).to_be_visible(timeout=1000)
	email_field.fill("jmills@cfc.co")

	password_field = page.get_by_role("textbox", name="Password")
	expect(password_field).to_be_visible(timeout=1000)
	password_field.fill("admin")

	login_button = page.get_by_role("button", name="Login")
	expect(login_button).to_be_visible(timeout=1000)
	login_button.click()
	expect(page).to_have_url(re.compile(r"beam#/"), timeout=1000)
	yield


def open_first_operation_id_from_manufacture(page) -> str:
	"""Navigate Home -> Manufacture -> Work Order -> first Operation.

	Returns:
	        str: operation_id
	"""
	page.get_by_text("Manufacture").click()
	expect(page).to_have_url(re.compile(r"#/manufacture"), timeout=1000)

	list_item = page.locator("css=.beam_list-item").first
	expect(list_item).to_be_visible(timeout=1000)
	list_item.click()
	expect(page).to_have_url(re.compile(r"#/work_order/[^/]+/?$"), timeout=1000)

	operation_link = page.locator("a[href*='/operation/']").first
	expect(operation_link).to_be_visible(timeout=1000)
	operation_link.click()
	expect(page).to_have_url(re.compile(r"#/work_order/[^/]+/operation/[^/?#]+"), timeout=1000)

	match = re.search(r"#/work_order/([^/]+)/operation/([^/?#]+)", page.url)
	assert match, f"Could not parse operation route from URL: {page.url}"
	return match.group(2)


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
	qty_input.fill(qty)
	page.get_by_role("button", name="Confirm").click()


def pause_form_is_visible(page) -> bool:
	return page.locator(".qty-input-row input").first.is_visible()


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


@pytest.mark.order(1)
def test_operation_details_are_visible(page):
	operation_id = open_first_operation_id_from_manufacture(page)
	description_box, timer_text, toggle_button, finish_button = get_operation_elements(page)

	expect(description_box).to_be_visible(timeout=1000)
	expect(timer_text).to_be_visible(timeout=1000)
	expect(toggle_button).to_be_visible(timeout=1000)
	expect(finish_button).to_be_visible(timeout=1000)
	expect(toggle_button).to_contain_text(re.compile("Start|Pause"), timeout=1000)

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


@pytest.mark.order(2)
def test_start_operation_starts_timer_and_toggles_buttons(page):
	operation_id = open_first_operation_id_from_manufacture(page)
	_, timer_text, toggle_button, _ = get_operation_elements(page)

	expect(toggle_button).to_be_enabled(timeout=1000)
	with use_current_db_transaction():
		job_card = frappe.get_value(
			"Job Card",
			{"operation_id": operation_id},
			["name", "status"],
			as_dict=True,
		)

	assert job_card and job_card.get(
		"name"
	), f"Expected a Job Card linked to operation {operation_id}"

	# Determine expected initial label from Job Card status and latest time log
	expected_label = "Start"
	# check latest time log first — an open time log means the operation is running
	last_logs = frappe.get_all(
		"Job Card Time Log",
		filters={"parent": job_card.get("name")},
		fields=["from_time", "to_time"],
		order_by="creation desc",
		limit=1,
	)
	if last_logs and last_logs[0].get("from_time") and not last_logs[0].get("to_time"):
		expected_label = "Pause"
	# if the job card is explicitly On Hold, treat as paused (Start)
	if job_card.get("status") == "On Hold":
		expected_label = "Start"

	page.wait_for_timeout(1000)
	with use_current_db_transaction():
		job_card = frappe.get_value(
			"Job Card",
			{"operation_id": operation_id},
			["name", "status"],
			as_dict=True,
		)
		expected_label = "Start"
		last_logs = frappe.get_all(
			"Job Card Time Log",
			filters={"parent": job_card.get("name")},
			fields=["from_time", "to_time"],
			order_by="creation desc",
			limit=1,
		)
		if last_logs and last_logs[0].get("from_time") and not last_logs[0].get("to_time"):
			expected_label = "Pause"
		if job_card.get("status") == "On Hold":
			expected_label = "Start"
	label = toggle_button.inner_text().strip()
	expect(toggle_button).to_contain_text(expected_label, timeout=1000)

	if label == "Pause":
		toggle_button.click()
		confirm_pause_with_qty(page)
		expect(toggle_button).to_contain_text("Start", timeout=10000)
	elif label != "Start":
		pytest.fail(f"Unexpected toggle label before start: {label}")

	initial_elapsed = timer_text.inner_text().strip()
	assert re.fullmatch(r"\d{2}:\d{2}:\d{2}", initial_elapsed)

	toggle_button.click()
	expect(toggle_button).to_be_enabled(timeout=10000)
	expect(toggle_button).to_contain_text("Pause", timeout=10000)

	page.wait_for_timeout(1500)
	updated_elapsed = timer_text.inner_text().strip()
	assert re.fullmatch(r"\d{2}:\d{2}:\d{2}", updated_elapsed)
	assert hms_to_seconds(updated_elapsed) > hms_to_seconds(initial_elapsed)

	with use_current_db_transaction():
		job_card_name = frappe.get_value("Job Card", {"operation_id": operation_id}, "name")

	assert job_card_name, f"Expected a Job Card linked to operation {operation_id}"


@pytest.mark.order(3)
def test_stop_operation_stops_timer_and_records_time_log(page):
	operation_id = open_first_operation_id_from_manufacture(page)
	_, timer_text, toggle_button, _ = get_operation_elements(page)

	with use_current_db_transaction():
		job_card_name = frappe.get_value("Job Card", {"operation_id": operation_id}, "name")
		initial_logs = frappe.get_all(
			"Job Card Time Log",
			filters={"parent": job_card_name},
			fields=["name", "from_time", "to_time", "time_in_mins"],
		)

	assert job_card_name, f"Expected a Job Card linked to operation {operation_id}"
	initial_closed_logs = len([log for log in initial_logs if log.to_time])

	ensure_operation_running(page, toggle_button)

	page.wait_for_timeout(1200)
	timer_after_start = timer_text.inner_text().strip()

	toggle_button.click()
	confirm_pause_with_qty(page)
	expect(toggle_button).to_contain_text("Start", timeout=10000)

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
			fields=["name", "from_time", "to_time", "time_in_mins"],
		)

	final_closed_logs = len([log for log in final_logs if log.to_time])
	assert final_closed_logs >= initial_closed_logs + 1
	assert any(
		log.to_time for log in final_logs
	), "Expected the stopped job card to have a closed time log"
