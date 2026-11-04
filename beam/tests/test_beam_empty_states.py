# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

pytest_plugins = ["beam.tests.playwright_fixtures"]

import re

import pytest
from playwright.sync_api import expect

from beam.tests.playwright_utils import goto_beam_portal_route

NO_RESULTS_FOR_FILTERS = "No results for these filters"

# route, request that feeds the list, empty-list message, first filter choice (None: no filters)
EMPTY_LISTS = {
	"pick": (
		"pick-list",
		re.compile(r"/api/resource/Pick(%20| )List(\?|$)"),
		"No open pick lists",
		None,
	),
	"receive": (
		"receive",
		re.compile(r"/api/method/beam\.beam\.demand\.receiving\.get_receiving_demand"),
		"Nothing to receive",
		"Unallocated",
	),
	"ship": (
		"ship",
		re.compile(r"/api/method/beam\.beam\.demand\.demand\.get_demand"),
		"Nothing to ship",
		"Unallocated",
	),
	"demand": (
		"demand",
		re.compile(r"/api/method/beam\.beam\.demand\.demand\.get_demand"),
		"No open demand",
		"Unallocated",
	),
	"manufacture": (
		"manufacture",
		re.compile(r"/api/resource/Work(%20| )Order(\?|$)"),
		"No work orders",
		"Completed",
	),
}


def answer_with_no_rows(page, request_pattern):
	def respond(route):
		payload = {"data": []} if "/api/resource/" in route.request.url else {"message": []}
		route.fulfill(json=payload)

	page.route(request_pattern, respond)


@pytest.mark.order(360)
@pytest.mark.parametrize("name", list(EMPTY_LISTS))
def test_empty_list_says_why_it_is_empty(page, name):
	route, request_pattern, message, _ = EMPTY_LISTS[name]
	answer_with_no_rows(page, request_pattern)

	goto_beam_portal_route(page, route)

	expect(page.get_by_text(message, exact=True)).to_be_visible(timeout=15000)
	expect(page.locator(".beam_list-item")).to_have_count(0)


@pytest.mark.order(361)
@pytest.mark.parametrize("name", [name for name, spec in EMPTY_LISTS.items() if spec[3]])
def test_empty_filtered_list_says_no_results_for_filters(page, name):
	route, request_pattern, message, choice = EMPTY_LISTS[name]
	answer_with_no_rows(page, request_pattern)

	goto_beam_portal_route(page, route)
	expect(page.get_by_text(message, exact=True)).to_be_visible(timeout=15000)

	page.locator(".beam_filters-heading").click()
	page.locator(".beam_filter-option").first.click()
	page.locator("li.beam_filter-select-option").filter(has_text=choice).click()

	expect(page.get_by_text(NO_RESULTS_FOR_FILTERS, exact=True)).to_be_visible()
	expect(page.get_by_text(message, exact=True)).to_have_count(0)


@pytest.mark.order(362)
@pytest.mark.parametrize("name", ["receive", "ship", "demand", "manufacture"])
def test_list_with_rows_does_not_show_empty_message(page, name):
	route, _, message, _ = EMPTY_LISTS[name]

	goto_beam_portal_route(page, route)

	expect(page.locator(".beam_list-item").first).to_be_visible(timeout=15000)
	expect(page.get_by_text(message, exact=True)).to_have_count(0)
	expect(page.get_by_text(NO_RESULTS_FOR_FILTERS, exact=True)).to_have_count(0)
