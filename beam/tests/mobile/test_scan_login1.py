# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

# To test locally:
#  activate the virtual environment
#  bench start, and then run:
#  pytest ./beam/tests/mobile/test_scan_to_login.py --browser firefox --headed --base-url http://127.0.0.1:8000 --disable-warnings

import frappe
import pytest
from playwright.sync_api import expect

from beam.tests.test_utils import use_current_db_transaction

# NOTE: any navigation tests should be done using `expect(page).to_have_url` since
# `page.expect_navigation()` won't work with Beam's hash-based routes

LOGIN_USER = "support@agritheory.dev"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _set_scan_to_login(setting_value: str):
	"""
	Set BEAM Settings enable_scan_to_login field.

	Accepted values:
	  "All Users"         – any user with a barcode may scan to log in
	  "Mobile Users Only" – only users with the 'BEAM Mobile User' role
	"""
	with use_current_db_transaction():
		beam_settings = frappe.get_doc("BEAM Settings", "Ambrosia Pie Company")
		beam_settings.enable_scan_to_login = setting_value
		beam_settings.save()
		frappe.db.commit()


def _get_user_barcode(user_email: str) -> str:
	"""Return the first barcode assigned to the given user, asserting one exists."""
	with use_current_db_transaction():
		barcodes = frappe.get_all(
			"Item Barcode",
			filters={"parent": user_email, "parenttype": "User"},
			pluck="barcode",
		)
		assert barcodes, f"No barcodes found for user {user_email}"
		return barcodes[0]


def _full_url(base_url: str, path: str) -> str:
	"""Build a full URL from the pytest-playwright base_url fixture and a path."""
	return base_url.rstrip("/") + path


# ---------------------------------------------------------------------------
# Test: scan a valid user barcode → authenticated redirect to /beam
# ---------------------------------------------------------------------------


@pytest.mark.order(1)
def test_scan_valid_user_barcode_logs_in(page, base_url):
	"""
	Scenario: Login by scanning user barcode (enable_scan_to_login = "All Users")
	- Navigate to /login
	- Simulate scanning a valid user barcode
	- Expect redirect to /beam home page
	- Expect session authenticated as the scanned user
	"""
	_set_scan_to_login("All Users")

	user_barcode = _get_user_barcode(LOGIN_USER)

	page.goto(_full_url(base_url, "/login"))
	page.wait_for_load_state("networkidle")

	# Simulate badge scan on the login page
	page.evaluate("barcode => scanner.simulate(window, barcode)", user_barcode)
	page.wait_for_timeout(1500)

	# Should be redirected to the BEAM home page
	expect(page).to_have_url(_full_url(base_url, "/beam"))

	# Confirm the session belongs to the scanned user
	with use_current_db_transaction():
		session_user = frappe.session.user
	assert (
		session_user == LOGIN_USER
	), f"Expected session user {LOGIN_USER!r} after scan login, got {session_user!r}"


# ---------------------------------------------------------------------------
# Test: scan a non-user barcode at login → error, remain on /login
# ---------------------------------------------------------------------------


@pytest.mark.order(2)
def test_scan_invalid_login_barcode_shows_error(page, base_url):
	"""
	Scenario: Reject invalid login barcode
	- Navigate to /login
	- Simulate scanning a barcode belonging to an Item (not a User)
	- Expect error message "Wrong barcode"
	- Expect page remains on /login
	"""
	_set_scan_to_login("All Users")

	# Use an item barcode that is NOT a user barcode
	with use_current_db_transaction():
		item_barcodes = frappe.get_all(
			"Item Barcode",
			filters={"parenttype": "Item"},
			pluck="barcode",
			limit=1,
		)
		assert item_barcodes, "No Item barcodes found in test data"
	non_user_barcode = item_barcodes[0]

	login_url = _full_url(base_url, "/login")
	page.goto(login_url)
	page.wait_for_load_state("networkidle")

	page.evaluate("barcode => scanner.simulate(window, barcode)", non_user_barcode)
	page.wait_for_timeout(1000)

	# Error message must be visible
	expect(page.get_by_text("Wrong barcode")).to_be_visible()

	# Must remain on the login page (no redirect)
	expect(page).to_have_url(login_url)


# ---------------------------------------------------------------------------
# Test: Mobile Users Only – user without BEAM Mobile User role is rejected
# ---------------------------------------------------------------------------


@pytest.mark.order(3)
def test_non_mobile_user_rejected_when_restricted(page, base_url):
	"""
	Scenario: Enforce mobile user role restriction
	- BEAM Settings enable_scan_to_login = "Mobile Users Only"
	- A user who does NOT have the 'BEAM Mobile User' role scans their badge
	- Expect error message "Not Beam mobile user"
	- Expect page remains on /login
	"""
	_set_scan_to_login("Mobile Users Only")

	# Find a user who lacks the BEAM Mobile User role and has a barcode
	with use_current_db_transaction():
		all_users = frappe.get_all(
			"User",
			filters={"enabled": 1},
			pluck="name",
		)
		non_mobile_barcode = None
		for u in all_users:
			if u in ("Administrator", "Guest"):
				continue
			roles = frappe.get_roles(u)
			if "BEAM Mobile User" not in roles:
				barcodes = frappe.get_all(
					"Item Barcode",
					filters={"parent": u, "parenttype": "User"},
					pluck="barcode",
				)
				if barcodes:
					non_mobile_barcode = barcodes[0]
					break

	assert non_mobile_barcode, (
		"Could not find a non-mobile user with a barcode. " "Add one in the test fixtures."
	)

	login_url = _full_url(base_url, "/login")
	page.goto(login_url)
	page.wait_for_load_state("networkidle")

	page.evaluate("barcode => scanner.simulate(window, barcode)", non_mobile_barcode)
	page.wait_for_timeout(1000)

	# Error message must be visible
	expect(page.get_by_text("Not Beam mobile user")).to_be_visible()

	# Must remain on the login page
	expect(page).to_have_url(login_url)


# ---------------------------------------------------------------------------
# Test: IP restriction – allowed IP succeeds
# ---------------------------------------------------------------------------


@pytest.mark.order(4)
def test_ip_restriction_allows_configured_ip(page, base_url):
	"""
	Scenario: Enforce IP restriction – scan from allowed IP succeeds
	- BEAM Settings restrict_ip set to 127.0.0.1 (local bench)
	- Scan a valid user barcode
	- Login succeeds and redirects to /beam
	"""
	_set_scan_to_login("All Users")

	allowed_ip = "127.0.0.1"
	with use_current_db_transaction():
		beam_settings = frappe.get_doc("BEAM Settings", "Ambrosia Pie Company")
		beam_settings.restrict_ip = allowed_ip
		beam_settings.save()
		frappe.db.commit()

	user_barcode = _get_user_barcode(LOGIN_USER)

	page.goto(_full_url(base_url, "/login"))
	page.wait_for_load_state("networkidle")

	page.evaluate("barcode => scanner.simulate(window, barcode)", user_barcode)
	page.wait_for_timeout(1500)

	# Allowed IP → redirect to BEAM home
	expect(page).to_have_url(_full_url(base_url, "/beam"))

	# Teardown: remove IP restriction
	with use_current_db_transaction():
		beam_settings = frappe.get_doc("BEAM Settings", "Ambrosia Pie Company")
		beam_settings.restrict_ip = ""
		beam_settings.save()
		frappe.db.commit()


# ---------------------------------------------------------------------------
# Test: IP restriction – disallowed IP is rejected
# ---------------------------------------------------------------------------


@pytest.mark.order(5)
def test_ip_restriction_blocks_disallowed_ip(page, base_url):
	"""
	Scenario: Enforce IP restriction – scan from disallowed IP is rejected
	- BEAM Settings restrict_ip set to an address that will never match 127.0.0.1
	- Scan a valid user barcode
	- Expect error message "Network not available"
	- Expect page remains on /login
	"""
	_set_scan_to_login("All Users")

	# 192.0.2.x is IETF TEST-NET – will never be the actual local runner IP
	disallowed_ip = "192.0.2.255"
	with use_current_db_transaction():
		beam_settings = frappe.get_doc("BEAM Settings", "Ambrosia Pie Company")
		beam_settings.restrict_ip = disallowed_ip
		beam_settings.save()
		frappe.db.commit()

	user_barcode = _get_user_barcode(LOGIN_USER)

	login_url = _full_url(base_url, "/login")
	page.goto(login_url)
	page.wait_for_load_state("networkidle")

	page.evaluate("barcode => scanner.simulate(window, barcode)", user_barcode)
	page.wait_for_timeout(1000)

	# Error message must be visible
	expect(page.get_by_text("Network not available")).to_be_visible()

	# Must remain on the login page
	expect(page).to_have_url(login_url)

	# Teardown: remove IP restriction
	with use_current_db_transaction():
		beam_settings = frappe.get_doc("BEAM Settings", "Ambrosia Pie Company")
		beam_settings.restrict_ip = ""
		beam_settings.save()
		frappe.db.commit()
