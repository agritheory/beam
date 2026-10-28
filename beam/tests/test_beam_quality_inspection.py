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
from beam.tests.playwright_utils import use_current_db_transaction
from beam.tests.quality_inspection_fixtures import (
	BEAM_QI_ITEM,
	ensure_beam_qi_draft_receipt,
	ensure_beam_qi_purchase_order,
)

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


@pytest.mark.order(360)
def test_awaiting_inspection_list(page, setup):
	page.get_by_text("Inspect").click()
	page.wait_for_url("**/beam#/inspect")
	expect(page.get_by_text(BEAM_QI_ITEM).first).to_be_visible()


@pytest.mark.order(361)
def test_quality_inspection_accept_with_samples(page, setup):
	with use_current_db_transaction():
		from beam.tests.setup import seed_settings

		settings = seed_settings()
		pr_name = ensure_beam_qi_draft_receipt(settings)
		po_name = ensure_beam_qi_purchase_order(settings)

	page.goto(f"/beam#/purchase-receipt/{po_name}")
	page.wait_for_timeout(1000)

	inspect_link = page.get_by_role("link", name="Inspection required").first
	expect(inspect_link).to_be_visible()
	inspect_link.click()
	page.wait_for_url("**/inspect/**")

	page.locator("#sample-size").fill("3")
	page.get_by_label("Diameter sample 1").fill("11")
	page.get_by_label("Diameter sample 2").fill("11.2")
	page.get_by_label("Diameter sample 3").fill("10.9")
	page.get_by_label("Weight sample 1").fill("4.6")
	page.get_by_label("Weight sample 2").fill("4.7")
	page.get_by_label("Weight sample 3").fill("4.8")
	page.get_by_label("Color reading").fill("Natural")
	page.get_by_role("button", name="Accept").click()

	apply_init_script(page, MOCK_CAMERA)
	page.get_by_role("button", name="Open camera").click()
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
		second_row = [line for line in lines if line["state"] == "needed"][0]

		submit_inspection(
			"Purchase Receipt",
			pr_name,
			second_row["row"],
			3,
			{
				"Diameter": ["11", "11", "11"],
				"Weight": ["1", "1", "1"],
				"Color": ["Natural"],
				"Visual": ["Accepted"],
			},
		)

	with use_current_db_transaction():
		lines = get_line_inspections("Purchase Receipt", pr_name)
		rejected = [line for line in lines if line["state"] == "Rejected"]
		assert rejected


@pytest.mark.order(356)
def test_purchase_receipt_submit_after_rejected_qi(setup):
	with use_current_db_transaction():
		from beam.tests.setup import create_quarantine_warehouse, seed_settings

		settings = seed_settings()
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
def test_submitted_pr_blocks_qi_cancel(page, setup):
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
		qi = frappe.get_doc("Quality Inspection", result["name"])
		with pytest.raises(Exception):
			qi.cancel()


@pytest.mark.order(364)
def test_quarantine_release_when_inventory_tools_installed(page, setup):
	if not frappe.db.exists("DocType", "Inventory Tools Settings"):
		pytest.skip("Inventory Tools not installed on this bench")
