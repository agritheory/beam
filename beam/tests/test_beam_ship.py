# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

pytest_plugins = ["beam.tests.playwright_fixtures"]

import re

import frappe
import pytest
from playwright.sync_api import expect

from beam.tests.playwright_utils import (
	error_toast_text,
	open_desk_form,
	open_first_beam_list_row,
	order_id_from_beam_url,
	use_current_db_transaction,
	wait_for_docstatus,
)


@pytest.mark.order(340)
def test_ship_without_scanning(page):
	"""Test trying to ship without scanning any items"""
	# navigate to Ship -> Sales Order
	open_first_beam_list_row(page, "Ship", r"delivery-note")
	order_id = order_id_from_beam_url(page.url)
	assert order_id

	item = page.locator("css=.box .beam_list-item").first
	item_code, *others = item.inner_text().split("\n")

	# find all items in the list
	all_item_counts = page.locator("css=.box .beam_item-count")
	initial_counts = []
	for i in range(all_item_counts.count()):
		count_text = all_item_counts.nth(i).inner_text()
		initial_counts.append(count_text)

	# ensure all items start with 0 count
	for count in initial_counts:
		assert count.startswith("0/"), f"Expected item to start with 0/, but got: {count}"

	# count existing Delivery Notes before attempting to save
	with use_current_db_transaction():
		existing_notes = frappe.get_all(
			"Delivery Note Item",
			filters={
				"against_sales_order": order_id,
				"item_code": item_code,
				"owner": "support@agritheory.dev",
			},
			fields=["docstatus", "qty"],
		)
		initial_count = len(existing_notes)

	# try to click SAVE without scanning anything
	save_button = page.get_by_text("SAVE", exact=True)
	save_button.click()
	page.wait_for_timeout(1000)

	# verify no new draft Delivery Note was created
	with use_current_db_transaction():
		new_notes = frappe.get_all(
			"Delivery Note Item",
			filters={
				"against_sales_order": order_id,
				"item_code": item_code,
				"owner": "support@agritheory.dev",
			},
			fields=["docstatus", "qty"],
		)
		final_count = len(new_notes)
		assert (
			final_count == initial_count
		), f"Expected no new delivery notes, but count changed from {initial_count} to {final_count}"


@pytest.mark.order(341)
def test_complete_partial_shipment(page):
	"""Test completing a partial shipment"""
	open_first_beam_list_row(page, "Ship", r"delivery-note")
	order_id = order_id_from_beam_url(page.url)
	assert order_id

	# find the first item in the list
	item = page.locator("css=.box .beam_list-item").first
	item_code, *others = item.inner_text().split("\n")
	item_count = page.locator("css=.box .beam_item-count").first
	expect(item_count).to_have_text(re.compile("0/"))

	with use_current_db_transaction():
		barcodes = frappe.get_all(
			"Item Barcode", filters={"parenttype": "Item", "parent": item_code}, pluck="barcode"
		)
		assert len(barcodes) > 0

		# get the ordered quantity for validation
		so_items = frappe.get_all(
			"Sales Order Item",
			filters={"parent": order_id, "item_code": item_code},
			fields=["qty", "delivered_qty"],
		)

		assert len(so_items) > 0
		ordered_qty = so_items[0]["qty"]
		delivered_qty = so_items[0]["delivered_qty"]

	with page.expect_request(
		lambda request: request.headers.get("x-frappe-cmd") == "beam.beam.scan.scan"
	):
		page.evaluate("barcode => scanner.simulate(window, barcode)", barcodes[0])
		expect(item_count).to_have_text(re.compile("1/"))

	# ensure there are no existing Delivery Notes against this Sales Order for this item
	delivery_note = frappe.db.exists(
		"Delivery Note Item",
		{
			"docstatus": 0,
			"against_sales_order": order_id,
			"item_code": item_code,
			"owner": "support@agritheory.dev",
		},
	)
	assert not delivery_note

	# check that a draft Delivery Note is created
	page.get_by_text("SAVE", exact=True).click()
	page.wait_for_timeout(1000)
	with use_current_db_transaction():
		delivery_note = frappe.get_all(
			"Delivery Note Item",
			filters={"against_sales_order": order_id, "item_code": item_code},
			fields=["docstatus", "qty", "creation", "parent"],
			order_by="creation desc",
		)
	assert len(delivery_note) >= 1
	assert delivery_note[0]["docstatus"] == 0
	assert delivery_note[0]["qty"] == 1

	# check that the draft Delivery Note is submitted
	page.get_by_text("SHIP", exact=True).click()
	page.wait_for_timeout(1500)
	with use_current_db_transaction():
		delivery_note = frappe.get_all(
			"Delivery Note Item",
			filters={"against_sales_order": order_id, "item_code": item_code},
			fields=["docstatus", "qty", "creation"],
			order_by="creation desc",
			limit=1,
		)
	assert len(delivery_note) == 1
	assert delivery_note[0]["docstatus"] == 1
	assert delivery_note[0]["qty"] == 1

	# verify remaining qty is still available for future shipment
	with use_current_db_transaction():
		so_items = frappe.get_all(
			"Sales Order Item",
			filters={"parent": order_id, "item_code": item_code},
			fields=["qty", "delivered_qty"],
		)
		assert len(so_items) > 0
		new_delivered_qty = so_items[0]["delivered_qty"]
		assert new_delivered_qty == delivered_qty + 1
		assert new_delivered_qty < ordered_qty, "Should still have remaining qty available"


@pytest.mark.order(342)
def test_prevent_over_delivery(page):
	"""Test that system prevents over-delivery beyond ordered quantity"""
	open_first_beam_list_row(page, "Ship", r"delivery-note")
	order_id = order_id_from_beam_url(page.url)
	assert order_id

	item = page.locator("css=.box .beam_list-item").first
	item_code, *others = item.inner_text().split("\n")
	item_count = page.locator("css=.box .beam_item-count").first

	# get the ordered quantity and remaining quantity
	with use_current_db_transaction():
		barcodes = frappe.get_all(
			"Item Barcode", filters={"parenttype": "Item", "parent": item_code}, pluck="barcode"
		)
		assert len(barcodes) > 0

		so_items = frappe.get_all(
			"Sales Order Item",
			filters={"parent": order_id, "item_code": item_code},
			fields=["qty", "delivered_qty"],
		)
		assert len(so_items) > 0
		ordered_qty = so_items[0]["qty"]
		delivered_qty = so_items[0]["delivered_qty"]
		remaining_qty = ordered_qty - delivered_qty

	assert remaining_qty > 0

	# scan barcode beyond the remaining quantity
	scan_attempts = int(remaining_qty) + 5  # try to scan 5 more than allowed
	for i in range(scan_attempts):
		page.evaluate("barcode => scanner.simulate(window, barcode)", barcodes[0])
		page.wait_for_timeout(100)

	page.wait_for_timeout(500)

	count_text = item_count.inner_text()
	current_count = int(count_text.split("/")[0])
	assert (
		current_count <= remaining_qty
	), f"Count {current_count} should not exceed remaining qty {remaining_qty}"

	page.get_by_text("SAVE", exact=True).click()
	page.wait_for_timeout(1000)

	with use_current_db_transaction():
		notes = frappe.get_all(
			"Delivery Note Item",
			filters={"against_sales_order": order_id, "item_code": item_code},
			fields=["qty"],
			order_by="creation desc",
			limit=1,
		)
		if len(notes) > 0:
			assert notes[0]["qty"] <= remaining_qty, "Delivery Note qty should not exceed remaining qty"


@pytest.mark.order(343)
def test_cancel_submitted_delivery_note_workflow(page):
	"""Test cancelling a submitted Delivery Note through the complete workflow"""
	open_first_beam_list_row(page, "Ship", r"delivery-note")
	order_id = order_id_from_beam_url(page.url)
	assert order_id

	item = page.locator("css=.box .beam_list-item").first
	item_code, *others = item.inner_text().split("\n")

	with use_current_db_transaction():
		barcodes = frappe.get_all(
			"Item Barcode", filters={"parenttype": "Item", "parent": item_code}, pluck="barcode"
		)
		assert len(barcodes) > 0

	with page.expect_request(
		lambda request: request.headers.get("x-frappe-cmd") == "beam.beam.scan.scan"
	):
		page.evaluate("barcode => scanner.simulate(window, barcode)", barcodes[0])
		page.wait_for_timeout(500)

	page.get_by_text("SAVE", exact=True).click()
	page.wait_for_timeout(1000)

	# Verify draft Delivery Note was created
	with use_current_db_transaction():
		delivery_notes = frappe.get_all(
			"Delivery Note Item",
			filters={"against_sales_order": order_id, "item_code": item_code},
			fields=["docstatus", "parent"],
			order_by="creation desc",
			limit=1,
		)
		assert len(delivery_notes) > 0
		assert delivery_notes[0]["docstatus"] == 0
		dn_name = delivery_notes[0]["parent"]

	# Submit the Delivery Note
	ship_button = page.get_by_text("SHIP", exact=True)
	expect(ship_button).to_be_visible()
	ship_button.click()
	wait_for_docstatus("Delivery Note", dn_name, 1)

	# Verify CANCEL button is visible and SHIP button is hidden
	cancel_button = page.get_by_text("CANCEL", exact=True)
	expect(cancel_button).to_be_visible()
	expect(ship_button).not_to_be_visible()

	with use_current_db_transaction():
		sle_before = frappe.get_all(
			"Stock Ledger Entry",
			filters={"voucher_type": "Delivery Note", "voucher_no": dn_name},
			fields=["name", "actual_qty"],
		)
		sle_count_before = len(sle_before)
		assert sle_count_before > 0, "Should have stock ledger entries after submission"

	# Click CANCEL button
	cancel_button.click()
	page.wait_for_timeout(1000)

	# The portal reports a refused cancel only as a toast, so read it before
	# polling; otherwise a server-side rejection looks like a 20s timeout.
	rejected = error_toast_text(page)
	assert rejected is None, f"CANCEL was rejected: {rejected}"

	wait_for_docstatus("Delivery Note", dn_name, 2)

	with use_current_db_transaction():
		# Verify stock ledger entries were reversed
		sle_after = frappe.get_all(
			"Stock Ledger Entry",
			filters={"voucher_type": "Delivery Note", "voucher_no": dn_name},
			fields=["name", "actual_qty"],
		)
		sle_count_after = len(sle_after)

		# Should have double the entries (original + reversal)
		assert (
			sle_count_after == sle_count_before * 2
		), f"Expected {sle_count_before * 2} SLE entries, got {sle_count_after}"

	expect(cancel_button).not_to_be_visible()


@pytest.mark.order(344)
def test_cancel_submitted_delivery_note(page):
	"""Test cancelling a submitted Delivery Note from Desk."""
	with use_current_db_transaction():
		submitted_notes = frappe.get_all(
			"Delivery Note",
			filters={"docstatus": 1, "owner": "support@agritheory.dev"},
			fields=["name"],
			order_by="creation desc",
			limit=1,
		)

		assert (
			len(submitted_notes) > 0
		), "Should have at least one submitted Delivery Note from previous tests"
		dn_name = submitted_notes[0]["name"]

	open_desk_form(page, "delivery-note", dn_name)
	expect(page.locator(".page-head")).to_be_visible()

	# Primary toolbar Cancel, or Menu → Cancel (ERPNext often hides Cancel in Menu).
	cancel_button = page.locator(".page-actions").get_by_role("button", name="Cancel")
	if cancel_button.count() == 0 or not cancel_button.first.is_visible():
		menu = page.locator(".menu-btn-group > button, .page-actions .menu-btn-group button").first
		expect(menu).to_be_visible(timeout=10000)
		menu.click()
		cancel_button = page.locator(".dropdown-menu").get_by_text("Cancel", exact=True)

	expect(cancel_button.first).to_be_visible(timeout=10000)


@pytest.mark.order(345)
def test_unsaved_changes_warning(page):
	"""Test that user is warned when navigating away with unsaved changes"""
	open_first_beam_list_row(page, "Ship", r"delivery-note")
	order_id = order_id_from_beam_url(page.url)
	assert order_id

	unsaved_indicator = page.locator("span.dirty")
	expect(unsaved_indicator).not_to_be_visible()

	item = page.locator("css=.box .beam_list-item").first
	item_code, *others = item.inner_text().split("\n")

	with use_current_db_transaction():
		barcodes = frappe.get_all(
			"Item Barcode", filters={"parenttype": "Item", "parent": item_code}, pluck="barcode"
		)
		assert len(barcodes) > 0

	# Scan barcode to create unsaved changes
	with page.expect_request(
		lambda request: request.headers.get("x-frappe-cmd") == "beam.beam.scan.scan"
	):
		page.evaluate("barcode => scanner.simulate(window, barcode)", barcodes[0])
		page.wait_for_timeout(500)

	expect(unsaved_indicator).to_be_visible()
	expect(unsaved_indicator).to_have_text("Unsaved")

	should_accept = [False]

	def handle_dialog(dialog):
		if should_accept[0]:
			dialog.accept()
		else:
			dialog.dismiss()

	page.on("dialog", handle_dialog)

	# First attempt: dismiss the dialog
	home_link = page.get_by_role("link", name="Home")
	home_link.click()
	page.wait_for_timeout(500)

	# Verify we stayed on the same page (dialog was shown and dismissed)
	assert (
		"delivery-note" in page.url
	), "Should still be on delivery-note page after dismissing warning"

	# Second attempt: accept the dialog
	should_accept[0] = True
	home_link.click()
	page.wait_for_timeout(500)

	# Verify we navigated away (dialog was shown and accepted)
	assert (
		"delivery-note" not in page.url
	), "Should have left delivery-note page after accepting warning"


@pytest.mark.order(346)
def test_scan_handling_unit_on_delivery_note(page):
	"""Test scanning a handling unit barcode instead of item barcode"""
	open_first_beam_list_row(page, "Ship", r"delivery-note")
	order_id = order_id_from_beam_url(page.url)
	assert order_id

	item = page.locator("css=.box .beam_list-item").first
	item_code, *others = item.inner_text().split("\n")
	item_count = page.locator("css=.box .beam_item-count").first
	expect(item_count).to_have_text(re.compile("0/"))

	# find a handling unit with available stock for this item
	with use_current_db_transaction():
		hu_candidates = frappe.get_all(
			"Stock Ledger Entry",
			filters={"item_code": item_code, "warehouse": "Baked Goods - APC", "is_cancelled": 0},
			fields=["handling_unit", "SUM(actual_qty) AS stock_qty"],
			group_by="handling_unit",
			order_by="SUM(actual_qty) desc",
		)

		hu_candidates = [h for h in hu_candidates if h.handling_unit and h.stock_qty > 0]
		assert len(hu_candidates) > 0, f"No Handling Unit with stock found for item {item_code}"

		hu_name = hu_candidates[0]["handling_unit"]
		hu_stock_qty = hu_candidates[0]["stock_qty"]

		hu_barcode = frappe.db.get_value(
			"Item Barcode",
			{"parenttype": "Handling Unit", "parent": hu_name},
			"barcode",
		)
		assert hu_barcode, f"No barcode registered for Handling Unit {hu_name}"

		# get remaining qty on the SO to know what to expect on the form
		so_items = frappe.get_all(
			"Sales Order Item",
			filters={"parent": order_id, "item_code": item_code},
			fields=["qty", "delivered_qty"],
		)
		assert len(so_items) > 0
		remaining_so_qty = so_items[0]["qty"] - so_items[0]["delivered_qty"]
		assert remaining_so_qty > 0, "Sales Order has no remaining qty for this item"

	with page.expect_request(
		lambda request: request.headers.get("x-frappe-cmd") == "beam.beam.scan.scan"
	):
		page.evaluate("barcode => scanner.simulate(window, barcode)", hu_barcode)
		page.wait_for_timeout(500)

	# verify that count changed from 0 to a positive value
	count_text = item_count.inner_text()
	current_count = int(count_text.split("/")[0])
	expected_count = min(int(hu_stock_qty), int(remaining_so_qty))
	assert current_count == expected_count, (
		f"Expected count {expected_count} after scanning HU (hu_qty={hu_stock_qty}, "
		f"remaining_so_qty={remaining_so_qty}), got {current_count}"
	)

	page.get_by_text("SAVE", exact=True).click()
	page.wait_for_timeout(1000)

	# verify the draft Delivery Note was created with the handling_unit field populated
	with use_current_db_transaction():
		dn_items = frappe.get_all(
			"Delivery Note Item",
			filters={"against_sales_order": order_id, "item_code": item_code},
			fields=["docstatus", "qty", "handling_unit", "parent"],
			order_by="creation desc",
			limit=1,
		)
		assert len(dn_items) > 0, "No Delivery Note item was created"
		assert dn_items[0]["docstatus"] == 0, "Delivery Note should be in draft state"
		assert (
			dn_items[0]["handling_unit"] == hu_name
		), f"Expected handling_unit '{hu_name}' on DN item, got '{dn_items[0]['handling_unit']}'"
		assert (
			dn_items[0]["qty"] == expected_count
		), f"Expected qty {expected_count} on DN item, got {dn_items[0]['qty']}"
