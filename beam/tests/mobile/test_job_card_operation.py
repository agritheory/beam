# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import re

import frappe
import pytest
from playwright.sync_api import expect

from beam.tests.test_utils import use_current_db_transaction

# NOTE: any navigation tests should be done using `expect(page).to_have_url` since
# `page.expect_navigation()` won't work with Beam's hash-based routes


def open_first_operation_from_manufacture(page) -> tuple[str, str]:
	"""Navigate Home -> Manufacture -> Work Order -> first Operation.

	Returns:
	        tuple[str, str]: work_order_id, operation_id
	"""
	page.get_by_text("Manufacture").click()
	expect(page).to_have_url(re.compile(r"#/manufacture"), timeout=15000)

	page.locator("css=.beam_list-item").first.click()
	expect(page).to_have_url(re.compile(r"#/work_order/[^/]+/?$"), timeout=15000)

	operation_link = page.locator("a[href*='/operation/']").first
	expect(operation_link).to_be_visible(timeout=15000)
	operation_link.click()
	expect(page).to_have_url(re.compile(r"#/work_order/[^/]+/operation/[^/?#]+"), timeout=15000)

	match = re.search(r"#/work_order/([^/]+)/operation/([^/?#]+)", page.url)
	assert match, f"Could not parse operation route from URL: {page.url}"
	return match.group(1), match.group(2)


def hms_to_seconds(value: str) -> int:
	hours, minutes, seconds = (int(part) for part in value.split(":"))
	return (hours * 3600) + (minutes * 60) + seconds


@pytest.mark.order(13)
def test_operation_navigation_from_work_order(page):
	work_order_id, operation_id = open_first_operation_from_manufacture(page)
	assert work_order_id
	assert operation_id


@pytest.mark.order(14)
def test_operation_description_is_displayed(page):
	work_order_id, operation_id = open_first_operation_from_manufacture(page)
	description_box = page.locator("css=.container .box").first
	expect(description_box).to_be_visible(timeout=15000)

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
	else:
		# Some fixtures may not set description text; ensure the description area still renders.
		expect(page).to_have_url(
			re.compile(rf"#/work_order/{re.escape(work_order_id)}/operation/{re.escape(operation_id)}")
		)


@pytest.mark.order(15)
def test_operation_elapsed_time_is_visible_format_hh_mm_ss(page):
	_, operation_id = open_first_operation_from_manufacture(page)
	timer_text = page.locator("css=.fix-height b").first
	expect(timer_text).to_be_visible(timeout=15000)

	elapsed = timer_text.inner_text().strip()
	assert re.fullmatch(r"\d{2}:\d{2}:\d{2}", elapsed), f"Unexpected elapsed time format: {elapsed}"

	with use_current_db_transaction():
		job_card_name = frappe.get_value("Job Card", {"operation_id": operation_id}, "name")

	assert job_card_name, f"Expected a Job Card linked to operation {operation_id}"


@pytest.mark.order(16)
@pytest.mark.xfail(reason="Operation Start/Stop still TODO in Operation.vue")
def test_start_operation_starts_timer_and_toggles_buttons(page):
	_, _ = open_first_operation_from_manufacture(page)

	timer_text = page.locator("css=.fix-height b").first
	start_button = page.get_by_role("button", name="Start")
	stop_button = page.get_by_role("button", name="Stop")

	expect(timer_text).to_be_visible(timeout=15000)
	expect(start_button).to_be_enabled(timeout=15000)
	expect(stop_button).to_be_disabled(timeout=15000)

	initial_elapsed = timer_text.inner_text().strip()
	assert re.fullmatch(r"\d{2}:\d{2}:\d{2}", initial_elapsed)

	page.once("dialog", lambda dialog: dialog.dismiss())
	start_button.click()

	expect(start_button).to_be_disabled(timeout=5000)
	expect(stop_button).to_be_enabled(timeout=5000)

	page.wait_for_timeout(1500)
	updated_elapsed = timer_text.inner_text().strip()
	assert re.fullmatch(r"\d{2}:\d{2}:\d{2}", updated_elapsed)
	assert hms_to_seconds(updated_elapsed) > hms_to_seconds(initial_elapsed)


@pytest.mark.order(17)
@pytest.mark.xfail(reason="Operation Start/Stop still TODO in Operation.vue")
def test_stop_operation_stops_timer_and_creates_time_log(page):
	_, operation_id = open_first_operation_from_manufacture(page)

	timer_text = page.locator("css=.fix-height b").first
	start_button = page.get_by_role("button", name="Start")
	stop_button = page.get_by_role("button", name="Stop")

	with use_current_db_transaction():
		job_card_name = frappe.get_value("Job Card", {"operation_id": operation_id}, "name")
		initial_logs = frappe.get_all(
			"Job Card Time Log",
			filters={"parent": job_card_name},
			fields=["name", "from_time", "to_time", "time_in_mins"],
		)

	assert job_card_name

	page.once("dialog", lambda dialog: dialog.dismiss())
	start_button.click()
	expect(stop_button).to_be_enabled(timeout=5000)

	page.wait_for_timeout(1200)
	timer_after_start = timer_text.inner_text().strip()

	page.once("dialog", lambda dialog: dialog.dismiss())
	stop_button.click()

	expect(start_button).to_be_enabled(timeout=5000)
	expect(stop_button).to_be_disabled(timeout=5000)

	page.wait_for_timeout(1500)
	timer_after_stop = timer_text.inner_text().strip()
	page.wait_for_timeout(1200)
	timer_after_wait = timer_text.inner_text().strip()

	assert timer_after_wait == timer_after_stop
	assert hms_to_seconds(timer_after_stop) >= hms_to_seconds(timer_after_start)

	with use_current_db_transaction():
		final_logs = frappe.get_all(
			"Job Card Time Log",
			filters={"parent": job_card_name},
			fields=["name", "from_time", "to_time", "time_in_mins"],
		)

	assert len(final_logs) >= len(initial_logs) + 1
