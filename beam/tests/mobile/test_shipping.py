
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

	# get the selected Sales Order
	parsed_url = urlparse(page.url.replace("#", ""))
	path_parts = [p for p in parsed_url.path.split("/") if p]
	order_id = path_parts[-1] if path_parts else None
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

