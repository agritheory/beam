# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest
from playwright.sync_api import expect

from beam.tests.playwright_utils import use_current_db_transaction

MOBILE_USER_EMAIL = "dsolomon@cfc.co"  # Has "BEAM Mobile User" role
NON_MOBILE_USER_EMAIL = "mreynolds@cfc.co"  # Does NOT have "BEAM Mobile User" role


def get_user_barcode(user_email):
	"""Get the barcode for a user from the database"""
	barcode = frappe.db.get_value(
		"Item Barcode", {"parent": user_email, "parenttype": "User"}, "barcode"
	)
	return barcode


def set_beam_setting(field, value):
	"""Helper to update BEAM Settings for tests"""
	company = frappe.defaults.get_defaults().get("company")
	beam_settings = frappe.get_doc("BEAM Settings", {"company": company})
	beam_settings.set(field, value)
	beam_settings.save()
	frappe.db.commit()


def logout(page):
	page.goto(f"{frappe.utils.get_url()}/api/method/logout")
	page.wait_for_timeout(1000)


@pytest.mark.order(1)
def test_scan_to_login_success_all_users(page):
	"""Test successful login scanning - All Users mode"""
	with use_current_db_transaction():
		set_beam_setting("enable_scan_to_login", "All Users")
		mobile_user_barcode = get_user_barcode(MOBILE_USER_EMAIL)
		assert mobile_user_barcode, f"Barcode not found for user {MOBILE_USER_EMAIL}"

	# Navigate to login page
	page.goto(f"{frappe.utils.get_url()}/login")
	page.wait_for_load_state("networkidle")

	expect(page).to_have_url(frappe.utils.get_url() + "/login#login")

	with page.expect_request(
		lambda request: request.headers.get("x-frappe-cmd") == "beam.beam.scan.user_login.scan_login"
	):
		page.evaluate(
			"barcode => window.scanHandler.scanner.simulate(document, barcode)", mobile_user_barcode
		)

	page.wait_for_timeout(2000)
	expect(page).to_have_url(frappe.utils.get_url() + "/beam#/")

	# Verify user is authenticated by checking session in browser
	logged_in_user = page.evaluate("() => frappe.session.user")
	assert logged_in_user == MOBILE_USER_EMAIL, f"Expected {MOBILE_USER_EMAIL}, got {logged_in_user}"

	logout(page)


@pytest.mark.order(2)
def test_scan_to_login_invalid_barcode(page):
	"""Test rejection of non-user barcode"""
	with use_current_db_transaction():
		set_beam_setting("enable_scan_to_login", "All Users")
		item_barcode = frappe.get_value("Item Barcode", {"parent": "Butter"}, "barcode")
		assert item_barcode, "Item barcode not found for test"

	# Navigate to login page
	page.goto(f"{frappe.utils.get_url()}/login#login")
	page.wait_for_load_state("networkidle")

	page.evaluate("barcode => window.scanHandler.scanner.simulate(document, barcode)", item_barcode)
	page.wait_for_timeout(1000)

	# Verify error message appears
	error_message = page.locator(".msgprint-dialog .modal-body")
	expect(error_message).to_be_visible(timeout=5000)
	expect(error_message).to_contain_text("Wrong barcode")

	# Verify we're still on login page
	expect(page).to_have_url(frappe.utils.get_url() + "/login#login")


@pytest.mark.order(3)
def test_scan_to_login_mobile_users_only_success(page):
	"""Test login with mobile user role restriction - success case"""
	with use_current_db_transaction():
		set_beam_setting("enable_scan_to_login", "Mobile Users Only")

		mobile_user_barcode = get_user_barcode(MOBILE_USER_EMAIL)
		assert mobile_user_barcode, f"Barcode not found for user {MOBILE_USER_EMAIL}"

	page.goto(f"{frappe.utils.get_url()}/login")
	page.wait_for_load_state("networkidle")

	with page.expect_request(
		lambda request: request.headers.get("x-frappe-cmd") == "beam.beam.scan.user_login.scan_login"
	):
		page.evaluate(
			"barcode => window.scanHandler.scanner.simulate(document, barcode)", mobile_user_barcode
		)

	page.wait_for_timeout(2000)
	expect(page).to_have_url(frappe.utils.get_url() + "/beam#/")

	logged_in_user = page.evaluate("() => frappe.session.user")
	assert logged_in_user == MOBILE_USER_EMAIL

	logout(page)


@pytest.mark.order(4)
def test_scan_to_login_mobile_users_only_reject(page):
	"""Test rejection when user lacks BEAM Mobile User role"""
	with use_current_db_transaction():
		set_beam_setting("enable_scan_to_login", "Mobile Users Only")
		non_mobile_user_barcode = get_user_barcode(NON_MOBILE_USER_EMAIL)
		assert non_mobile_user_barcode, f"Barcode not found for user {NON_MOBILE_USER_EMAIL}"

	page.goto(f"{frappe.utils.get_url()}/login")
	page.wait_for_load_state("networkidle")

	page.evaluate(
		"barcode => window.scanHandler.scanner.simulate(document, barcode)", non_mobile_user_barcode
	)
	page.wait_for_timeout(2000)

	error_message = page.locator(".msgprint-dialog .modal-body")
	expect(error_message).to_be_visible(timeout=2000)
	expect(error_message).to_contain_text("Not Beam mobile user")

	expect(page).to_have_url(frappe.utils.get_url() + "/login#login")


@pytest.mark.order(5)
def test_scan_to_login_disabled(page):
	"""Test login when scanning is disabled"""
	mobile_user_barcode = get_user_barcode(MOBILE_USER_EMAIL)
	assert mobile_user_barcode, f"Barcode not found for user {MOBILE_USER_EMAIL}"
	with use_current_db_transaction():
		set_beam_setting("enable_scan_to_login", "Not Allowed")

	page.goto(f"{frappe.utils.get_url()}/login")
	page.wait_for_load_state("networkidle")

	page.evaluate(
		"barcode => window.scanHandler.scanner.simulate(document, barcode)", mobile_user_barcode
	)
	page.wait_for_timeout(1000)

	error_message = page.locator(".msgprint-dialog .modal-body")
	expect(error_message).to_be_visible(timeout=2000)
	expect(error_message).to_contain_text("Login scanning is not allowed")

	expect(page).to_have_url(frappe.utils.get_url() + "/login#login")


@pytest.mark.order(6)
def test_scan_to_login_ip_restriction_allowed(page):
	"""Test IP restriction - allowed IP"""
	with use_current_db_transaction():
		set_beam_setting("enable_scan_to_login", "All Users")
		mobile_user_barcode = get_user_barcode(MOBILE_USER_EMAIL)
		assert mobile_user_barcode, f"Barcode not found for user {MOBILE_USER_EMAIL}"
		set_beam_setting("restrict_ip", "127.0.0.1")

	page.goto(f"{frappe.utils.get_url()}/login")
	page.wait_for_load_state("networkidle")

	# Scan user barcode (should work since we're on localhost)
	with page.expect_request(
		lambda request: request.headers.get("x-frappe-cmd") == "beam.beam.scan.user_login.scan_login"
	):
		page.evaluate(
			"barcode => window.scanHandler.scanner.simulate(document, barcode)", mobile_user_barcode
		)

	page.wait_for_timeout(2000)
	expect(page).to_have_url(frappe.utils.get_url() + "/beam#/")

	logged_in_user = page.evaluate("() => frappe.session.user")
	assert logged_in_user == MOBILE_USER_EMAIL

	logout(page)
	with use_current_db_transaction():
		set_beam_setting("restrict_ip", "")  # Clear IP restriction


@pytest.mark.order(7)
def test_scan_to_login_ip_restriction_blocked(page):
	"""Test IP restriction - blocked IP"""
	with use_current_db_transaction():
		set_beam_setting("enable_scan_to_login", "All Users")
		mobile_user_barcode = get_user_barcode(MOBILE_USER_EMAIL)
		assert mobile_user_barcode, f"Barcode not found for user {MOBILE_USER_EMAIL}"
		# Configure IP that won't match localhost (192.168.1.x subnet only)
		set_beam_setting("restrict_ip", "192.168.1.")

	page.goto(f"{frappe.utils.get_url()}/login")
	page.wait_for_load_state("networkidle")

	# Scan user barcode - should be rejected due to IP restriction
	page.evaluate(
		"barcode => window.scanHandler.scanner.simulate(document, barcode)", mobile_user_barcode
	)
	page.wait_for_timeout(1000)

	# Verify error message appears
	error_message = page.locator(".msgprint-dialog .modal-body")
	expect(error_message).to_be_visible(timeout=5000)
	expect(error_message).to_contain_text("Network not available")

	# Verify we're still on login page
	expect(page).to_have_url(frappe.utils.get_url() + "/login#login")

	with use_current_db_transaction():
		set_beam_setting("restrict_ip", "")


@pytest.mark.order(8)
def test_scan_to_login_disabled_user(page):
	"""Test rejection when user account is disabled"""
	with use_current_db_transaction():
		set_beam_setting("enable_scan_to_login", "All Users")

		user = frappe.get_doc("User", NON_MOBILE_USER_EMAIL)
		original_enabled_status = user.enabled

		# Temporarily disable the user
		user.enabled = 0
		user.save(ignore_permissions=True)
		frappe.db.commit()

		disabled_user_barcode = get_user_barcode(NON_MOBILE_USER_EMAIL)
		assert disabled_user_barcode, f"Barcode not found for user {NON_MOBILE_USER_EMAIL}"

	page.goto(f"{frappe.utils.get_url()}/login")
	page.wait_for_load_state("networkidle")

	# Scan disabled user barcode
	page.evaluate(
		"barcode => window.scanHandler.scanner.simulate(document, barcode)", disabled_user_barcode
	)
	page.wait_for_timeout(1000)

	error_message = page.locator(".msgprint-dialog .modal-body")
	expect(error_message).to_be_visible(timeout=5000)
	expect(error_message).to_contain_text("is disabled")

	expect(page).to_have_url(frappe.utils.get_url() + "/login#login")

	with use_current_db_transaction():
		user = frappe.get_doc("User", NON_MOBILE_USER_EMAIL)
		user.enabled = original_enabled_status
		user.save(ignore_permissions=True)
		frappe.db.commit()
