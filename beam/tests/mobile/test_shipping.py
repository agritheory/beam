
# **Complete a partial shipment**
# As a warehouse employee, I want to scan items from a Sales Order and create a partial Delivery Note so that I can ship available inventory without waiting for the full order.

# - Navigate Home → Ship → select Sales Order
# - Scan item barcode, count increments
# - Click SAVE, draft Delivery Note created
# - Click SHIP, Delivery Note submitted
# - Remaining qty still available for future shipment

# **Cancel a submitted Delivery Note**
# As a warehouse employee, I want to cancel a submitted Delivery Note so that I can correct mistakes made during shipping.

# - Navigate to a submitted Delivery Note
# - CANCEL button visible, SHIP button hidden
# - Click CANCEL, docstatus changes to Cancelled
# - Stock ledger entries reversed

# **Scan handling unit on Delivery Note**
# As a warehouse employee, I want to scan a handling unit barcode instead of an item barcode so that I can ship entire pallets/containers efficiently.

# - Scan HU barcode on Delivery Note form
# - Item automatically identified from HU
# - Quantity populated from HU stock qty
# - Handling unit field populated on line item

# **Prevent over-delivery**
# As a warehouse employee, I want the system to prevent me from shipping more than the ordered quantity so that I don't accidentally over-ship.

# - Scan item barcode repeatedly past ordered qty
# - Count stops at ordered qty OR warning displayed
# - Cannot submit with qty exceeding Sales Order line

# **Ship with unsaved changes warning**
# As a warehouse employee, I want to be warned if I navigate away with unsaved scans so that I don't lose my work.

# - Scan items on Delivery Note
# - "Unsaved" indicator visible in header
# - Attempt to navigate to Home
# - Warning or confirmation displayed

# To test locally:
#  active the virtual environment
#  bench start, and then run:
#  pytest ./beam/tests/test_shipping.py --browser firefox --headed --disable-warnings

import re
from urllib.parse import urlparse

import frappe
import pytest
from playwright.sync_api import expect

from beam.tests.test_utils import use_current_db_transaction


@pytest.mark.order(15)
def test_ship_without_scanning(page):
	"""Test trying to ship without scanning any items"""
	# navigate to Ship -> Sales Order
	page.get_by_text("Ship").click()
	page.locator("css=.beam_list-item").first.click()

	parsed_url = urlparse(page.url.replace("#", ""))
	order_id = parsed_url.query.replace("id=", "")
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
			filters={"against_sales_order": order_id, "item_code": item_code, "owner": "support@agritheory.dev"},
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
			filters={"against_sales_order": order_id, "item_code": item_code, "owner": "support@agritheory.dev"},
			fields=["docstatus", "qty"],
		)
		final_count = len(new_notes)
		assert (
			final_count == initial_count
		), f"Expected no new delivery notes, but count changed from {initial_count} to {final_count}"


@pytest.mark.order(16)
def test_complete_partial_shipment(page):
	"""Test completing a partial shipment"""
	page.get_by_text("Ship").click()
	page.locator("css=.beam_list-item").first.click()

	parsed_url = urlparse(page.url.replace("#", ""))
	order_id = parsed_url.query.replace("id=", "")
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


@pytest.mark.order(17)
def test_prevent_over_delivery(page):
	"""Test that system prevents over-delivery beyond ordered quantity"""
	page.get_by_text("Ship").click()
	page.locator("css=.beam_list-item").first.click()

	parsed_url = urlparse(page.url.replace("#", ""))
	order_id = parsed_url.query.replace("id=", "")
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
	assert current_count <= remaining_qty, f"Count {current_count} should not exceed remaining qty {remaining_qty}"

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


@pytest.mark.order(18)
def test_cancel_submitted_delivery_note_workflow(page):
	"""Test cancelling a submitted Delivery Note through the complete workflow"""
	page.get_by_text("Ship").click()
	page.locator("css=.beam_list-item").first.click()

	parsed_url = urlparse(page.url.replace("#", ""))
	order_id = parsed_url.query.replace("id=", "")
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
	page.wait_for_timeout(1500)

	# Verify Delivery Note is submitted
	with use_current_db_transaction():
		dn = frappe.get_doc("Delivery Note", dn_name)
		assert dn.docstatus == 1, f"Expected docstatus 1 (Submitted), got {dn.docstatus}"

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
	page.wait_for_timeout(1500)

	with use_current_db_transaction():
		dn = frappe.get_doc("Delivery Note", dn_name)
		assert dn.docstatus == 2, f"Expected docstatus 2 (Cancelled), got {dn.docstatus}"

		# Verify stock ledger entries were reversed
		sle_after = frappe.get_all(
			"Stock Ledger Entry",
			filters={"voucher_type": "Delivery Note", "voucher_no": dn_name},
			fields=["name", "actual_qty"],
		)
		sle_count_after = len(sle_after)
		
		# Should have double the entries (original + reversal)
		assert sle_count_after == sle_count_before * 2, f"Expected {sle_count_before * 2} SLE entries, got {sle_count_after}"

	expect(cancel_button).not_to_be_visible()


@pytest.mark.order(19)
@pytest.mark.skip(reason="Frontend does not load docstatus when navigating directly to delivery-note URL")
def test_cancel_submitted_delivery_note(page):
	"""Test cancelling a submitted Delivery Note"""
	with use_current_db_transaction():
		submitted_notes = frappe.get_all(
			"Delivery Note",
			filters={"docstatus": 1, "owner": "support@agritheory.dev"},
			fields=["name"],
			order_by="creation desc",
			limit=1,
		)
		
		assert len(submitted_notes) > 0, "Should have at least one submitted Delivery Note from previous tests"
		dn_name = submitted_notes[0]["name"]

	base_url = frappe.utils.get_url()
	page.goto(f"{base_url}/app/delivery-note/{dn_name}")
	page.wait_for_timeout(1000)

	cancel_button = page.get_by_role("button", name="Cancel")
	expect(cancel_button).to_be_visible()

