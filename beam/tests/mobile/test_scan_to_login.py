# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest
from playwright.sync_api import expect

from beam.tests.test_utils import use_current_db_transaction

MOBILE_USER_EMAIL = "dsolomon@cfc.co"  # Has "BEAM Mobile User" role
NON_MOBILE_USER_EMAIL = "mreynolds@cfc.co"  # Does NOT have "BEAM Mobile User" role


def get_user_barcode(user_email):
	"""Get the barcode for a user from the database"""
	barcode = frappe.db.get_value(
		"Item Barcode",
		{"parent": user_email, "parenttype": "User"},
		"barcode"
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


@pytest.mark.order(7)
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
		page.evaluate("barcode => window.scanHandler.scanner.simulate(document, barcode)", mobile_user_barcode)
	
	page.wait_for_timeout(2000)
	expect(page).to_have_url(frappe.utils.get_url() + "/beam#/")
	
	# Verify user is authenticated by checking session in browser
	logged_in_user = page.evaluate("() => frappe.session.user")
	assert logged_in_user == MOBILE_USER_EMAIL, f"Expected {MOBILE_USER_EMAIL}, got {logged_in_user}"
	
	logout(page)


@pytest.mark.order(8)
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


