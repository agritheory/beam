# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

pytest_plugins = ["beam.tests.playwright_fixtures"]

import frappe
import pytest
from frappe.utils import flt
from playwright.sync_api import expect

from beam.beam.quality_inspection import (
	discard_inspection_draft,
	get_line_inspections,
	open_inspection,
	qi_state,
	save_inspection_draft,
	submit_inspection,
)
from beam.tests.playwright_utils import goto_beam_portal_route, use_current_db_transaction
from beam.tests.quality_inspection_fixtures import (
	BEAM_QI_ITEM,
	disable_flour_incoming_inspection,
	enable_flour_incoming_inspection,
	ensure_beam_qi_draft_receipt,
	ensure_beam_qi_draft_receipt_committed,
	purchase_order_for_receipt,
)


@pytest.fixture(scope="module", autouse=True)
def flour_requires_inspection_for_qi_tests():
	"""Flour incoming inspection applies only during this module (not global fixtures)."""
	enable_flour_incoming_inspection()
	frappe.db.commit()
	yield
	disable_flour_incoming_inspection()
	frappe.db.commit()


MOCK_CAMERA = (
	"""
	Object.defineProperty(window, 'isSecureContext', { value: true, configurable: true });
"""
	+ """
	Object.defineProperty(navigator, 'mediaDevices', {
		value: {
			enumerateDevices: async () => [{ kind: 'videoinput', deviceId: 'mock', label: 'Mock', groupId: 'g' }],
			getUserMedia: async () => {
				const canvas = document.createElement('canvas');
				canvas.width = 640;
				canvas.height = 480;
				return canvas.captureStream(30);
			}
		},
		writable: false,
		configurable: true
	});
"""
)


def apply_init_script(page, script):
	page.add_init_script(script)
	page.reload()


def expand_inspection_parameter(page, parameter: str) -> None:
	section = page.locator(f'[data-inspection-parameter="{parameter}"]')
	expect(section).to_be_visible()
	body = section.locator(".inspection-parameter-body")
	if not body.is_visible():
		section.locator("button.inspection-parameter-header").click()
	expect(body).to_be_visible()


def fill_numeric_parameter(page, parameter: str, values: list[str]) -> None:
	expand_inspection_parameter(page, parameter)
	section = page.locator(f'[data-inspection-parameter="{parameter}"]')
	for index, value in enumerate(values, start=1):
		field = section.locator(f"#qi-{parameter}-{index}")
		while field.count() == 0:
			section.get_by_role("button", name="Add a reading").click()
			field = section.locator(f"#qi-{parameter}-{index}")
		field.fill(value)


def fill_text_parameter(page, parameter: str, value: str) -> None:
	expand_inspection_parameter(page, parameter)
	page.locator(f"#qi-{parameter}-1").fill(value)


def choose_passfail(page, parameter: str, choice: str) -> None:
	expand_inspection_parameter(page, parameter)
	page.locator(f'[data-inspection-parameter="{parameter}"]').get_by_role(
		"button", name=choice
	).click()


@pytest.mark.order(360)
def test_awaiting_inspection_list(page, setup):
	with use_current_db_transaction():
		from beam.tests.setup import seed_settings

		ensure_beam_qi_draft_receipt_committed(seed_settings())
	page.get_by_text("Inspect").click()
	page.wait_for_url("**/beam#/inspect")
	expect(page.get_by_text(BEAM_QI_ITEM).first).to_be_visible()


@pytest.mark.order(361)
def test_quality_inspection_accept_with_samples(page, setup):
	# Login fixture loads /beam over HTTP first; Camera.vue hides the FAB unless
	# isSecureContext is true at mount. Reload after registering the mock (same as test_beam_camera).
	apply_init_script(page, MOCK_CAMERA)

	with use_current_db_transaction():
		from beam.tests.setup import seed_settings

		settings = seed_settings()
		pr_name = ensure_beam_qi_draft_receipt_committed(settings)
		po_name = purchase_order_for_receipt(pr_name)

	goto_beam_portal_route(page, f"purchase-receipt/{po_name}")
	page.wait_for_timeout(1000)

	inspect_link = page.get_by_role("link", name="Inspection required").first
	expect(inspect_link).to_be_visible()
	inspect_link.click()
	page.wait_for_url("**/inspect/**")
	expect(page.locator(".inspection-shell").first).to_be_visible(timeout=15000)

	fill_numeric_parameter(page, "Diameter", ["11", "11.2", "10.9"])
	fill_numeric_parameter(page, "Weight", ["4.6", "4.7", "4.8"])
	fill_text_parameter(page, "Color", "Natural")
	choose_passfail(page, "Visual", "Accept")

	expect(page.locator(".camera-panel")).to_be_visible(timeout=10000)
	page.get_by_role("button", name="Open camera").click()
	expect(page.get_by_role("dialog", name="Camera")).to_be_visible()
	page.get_by_role("tab", name="Photo").click()
	page.get_by_role("button", name="Take photo").click()
	page.get_by_role("button", name="Attach (1)").click()

	page.get_by_role("button", name="SUBMIT").click()
	page.wait_for_timeout(1500)
	expect(page.get_by_text("Accepted")).to_be_visible()

	with use_current_db_transaction():
		lines = get_line_inspections("Purchase Receipt", pr_name)
		assert any(line["state"] == "Accepted" for line in lines)


@pytest.mark.order(362)
def test_quality_inspection_formula_reject(page, setup):
	with use_current_db_transaction():
		from beam.tests.setup import seed_settings

		pr_name = ensure_beam_qi_draft_receipt(seed_settings())
		lines = get_line_inspections("Purchase Receipt", pr_name)
		needed = [line for line in lines if line["state"] == "needed"]
		assert needed, lines
		row = needed[0]["row"]

		submit_inspection(
			"Purchase Receipt",
			pr_name,
			row,
			3,
			{
				"Diameter": ["11", "11", "11"],
				"Weight": ["1", "1", "1"],
				"Color": ["Natural"],
				"Visual": ["Accepted"],
			},
		)

		lines = get_line_inspections("Purchase Receipt", pr_name)
		rejected = [line for line in lines if line["state"] == "Rejected"]
		assert rejected


@pytest.mark.order(356)
def test_purchase_receipt_submit_after_rejected_qi(setup):
	with use_current_db_transaction():
		from beam.tests.setup import create_quarantine_warehouse, seed_settings

		settings = seed_settings()
		if not frappe.db.exists(
			"Warehouse", {"company": settings.company, "is_rejected_warehouse": 1, "disabled": 0}
		):
			create_quarantine_warehouse(settings)
		pr_name = ensure_beam_qi_draft_receipt(settings)
		lines = get_line_inspections("Purchase Receipt", pr_name)
		row = lines[0]["row"]
		submit_inspection(
			"Purchase Receipt",
			pr_name,
			row,
			1,
			{
				"Diameter": ["11"],
				"Weight": ["1"],
				"Color": ["Natural"],
				"Visual": ["Accepted"],
			},
		)
		pr = frappe.get_doc("Purchase Receipt", pr_name)
		for item in pr.items:
			if item.name == row:
				item.received_qty = item.qty
		pr.save()
		pr.submit()
		pr.reload()
		assert pr.docstatus == 1
		line = next(i for i in pr.items if i.name == row)
		assert flt(line.rejected_qty) == flt(line.received_qty)
		assert flt(line.qty) == 0
		assert line.rejected_warehouse


@pytest.mark.order(357)
def test_qi_state_reflects_submitted_document(setup):
	with use_current_db_transaction():
		from beam.tests.setup import seed_settings

		pr_name = ensure_beam_qi_draft_receipt(seed_settings())
		lines = get_line_inspections("Purchase Receipt", pr_name)
		row = lines[0]["row"]
		result = submit_inspection(
			"Purchase Receipt",
			pr_name,
			row,
			1,
			{
				"Diameter": ["11"],
				"Weight": ["5.1"],
				"Color": ["Natural"],
				"Visual": ["Accepted"],
			},
		)
		state, qi_status = qi_state(result["name"])
		assert state == "Accepted"
		assert qi_status == "Accepted"
		line = next(
			entry for entry in get_line_inspections("Purchase Receipt", pr_name) if entry["row"] == row
		)
		assert line["state"] == "Accepted"


@pytest.mark.order(358)
def test_save_inspection_draft_reuses_same_qi(setup):
	with use_current_db_transaction():
		from beam.tests.setup import seed_settings

		pr_name = ensure_beam_qi_draft_receipt(seed_settings())
		lines = get_line_inspections("Purchase Receipt", pr_name)
		row = lines[0]["row"]
		answers = {"Diameter": ["11"], "Color": ["Natural"]}
		first = save_inspection_draft("Purchase Receipt", pr_name, row, 1, answers)
		second = save_inspection_draft(
			"Purchase Receipt",
			pr_name,
			row,
			1,
			{**answers, "Weight": ["5.1"], "Visual": ["Accepted"]},
		)
		assert first["name"] == second["name"]
		qi = frappe.get_doc("Quality Inspection", first["name"])
		assert qi.docstatus == 0
		assert frappe.db.get_value("Purchase Receipt Item", row, "quality_inspection") == qi.name
		diameter = next(r for r in qi.readings if r.specification == "Diameter")
		assert flt(diameter.reading_1) == 11
		color = next(r for r in qi.readings if r.specification == "Color")
		assert color.reading_value == "Natural"
		visual = next(r for r in qi.readings if r.specification == "Visual")
		assert visual.status == "Accepted"


@pytest.mark.order(359)
def test_save_inspection_draft_incremental_then_discard(setup):
	with use_current_db_transaction():
		from beam.tests.setup import seed_settings

		pr_name = ensure_beam_qi_draft_receipt(seed_settings())
		lines = get_line_inspections("Purchase Receipt", pr_name)
		row = lines[0]["row"]
		first = save_inspection_draft("Purchase Receipt", pr_name, row, 1, {"Diameter": ["11"]})
		qi_name = first["name"]
		save_inspection_draft("Purchase Receipt", pr_name, row, 1, {"Color": ["Natural"]})
		qi = frappe.get_doc("Quality Inspection", qi_name)
		assert flt(next(r for r in qi.readings if r.specification == "Diameter").reading_1) == 11
		assert next(r for r in qi.readings if r.specification == "Color").reading_value == "Natural"

		discard_inspection_draft("Purchase Receipt", pr_name, row)
		assert not frappe.db.exists("Quality Inspection", qi_name)
		assert not frappe.db.get_value("Purchase Receipt Item", row, "quality_inspection")
		opened = open_inspection("Purchase Receipt", pr_name, row)
		assert opened["editable"]
		assert not opened.get("quality_inspection")


@pytest.mark.order(363)
def test_qi_cancel_after_pr_submit_clears_line_link(setup):
	with use_current_db_transaction():
		from beam.tests.setup import seed_settings

		pr_name = ensure_beam_qi_draft_receipt(seed_settings())
		lines = get_line_inspections("Purchase Receipt", pr_name)
		row = lines[0]["row"]
		result = submit_inspection(
			"Purchase Receipt",
			pr_name,
			row,
			1,
			{
				"Diameter": ["11"],
				"Weight": ["5"],
				"Color": ["Natural"],
				"Visual": ["Accepted"],
			},
		)
		pr = frappe.get_doc("Purchase Receipt", pr_name)
		pr.submit()
		assert frappe.db.get_value("Purchase Receipt Item", row, "quality_inspection") == result["name"]

		qi = frappe.get_doc("Quality Inspection", result["name"])
		qi.cancel()

		assert frappe.db.get_value("Quality Inspection", qi.name, "docstatus") == 2
		assert not frappe.db.get_value("Purchase Receipt Item", row, "quality_inspection")
		assert frappe.db.get_value("Purchase Receipt", pr_name, "docstatus") == 1


@pytest.mark.order(364)
def test_quarantine_release_when_inventory_tools_installed(page, setup):
	if not frappe.db.exists("DocType", "Inventory Tools Settings"):
		pytest.skip("Inventory Tools not installed on this bench")
