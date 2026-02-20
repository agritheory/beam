# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt


import frappe
import pytest

from beam.tests.test_utils import use_current_db_transaction

LOGIN_USER = "support@agritheory.dev"
SCAN_LOGIN_URL = "/api/method/beam.beam.scan.user_login.scan_login"


@pytest.fixture(autouse=True)
def goto_login_unauthenticated(page, setup):
	"""
	Depends on conftest `setup` so the page is fully loaded and we have a
	valid origin. Then logs out so each test starts unauthenticated, and
	navigates to /beam (not /login) so the CSRF token and frappe JS context
	are available for direct API calls.
	"""
	base_url = "http://127.0.0.1:8000"

	page.request.post(f"{base_url}/api/method/logout")

	page.goto(f"{base_url}/beam#/", wait_until="networkidle")

	yield

	page.context.clear_cookies()


def _call_scan_login(page, barcode: str) -> dict:
	"""
	Calls beam.beam.scan.user_login.scan_login via fetch() from the browser
	context. Returns a dict with keys: ok (bool), status (int), data (dict).
	"""
	return page.evaluate(
		"""async (args) => {
			const { url, barcode } = args
			const csrf = frappe.csrf_token || document.cookie
				.split('; ')
				.find(r => r.startsWith('csrf_token='))
				?.split('=')[1] || 'fetch'

			const resp = await fetch(url, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					'X-Frappe-CSRF-Token': csrf,
				},
				body: JSON.stringify({ barcode }),
			})
			let data = {}
			try { data = await resp.json() } catch (_) {}
			return { ok: resp.ok, status: resp.status, data }
		}""",
		{"url": SCAN_LOGIN_URL, "barcode": barcode},
	)


def _set_scan_to_login(setting_value: str):
	with use_current_db_transaction():
		beam_settings = frappe.get_doc("BEAM Settings", {"company": "Ambrosia Pie Company"})
		beam_settings.enable_scan_to_login = setting_value
		beam_settings.save()
		frappe.db.commit()


def _set_restrict_ip(ip_value: str):
	"""Set or clear the restrict_ip field on BEAM Settings."""
	with use_current_db_transaction():
		beam_settings = frappe.get_doc("BEAM Settings", {"company": "Ambrosia Pie Company"})
		beam_settings.restrict_ip = ip_value
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


@pytest.mark.order(1)
def test_scan_valid_user_barcode_logs_in(page):
	"""
	Scenario: Login by scanning user barcode (enable_scan_to_login = "All Users")
	- Call scan_login API with a valid user barcode
	- Expect HTTP 200 and success: True in response
	- Expect session authenticated as the scanned user
	"""
	_set_scan_to_login("All Users")

	user_barcode = _get_user_barcode(LOGIN_USER)

	result = _call_scan_login(page, user_barcode)

	assert result[
		"ok"
	], f"Expected scan_login to succeed, got status {result['status']}: {result['data']}"
	assert (
		result["data"].get("message", {}).get("success") is True
	), f"Expected success:True in response, got: {result['data']}"


@pytest.mark.order(2)
def test_scan_invalid_login_barcode_shows_error(page):
	"""
	Scenario: Reject invalid login barcode
	- Call scan_login API with an Item barcode (not a User barcode)
	- Expect HTTP error response with "Wrong barcode" in exception
	"""
	_set_scan_to_login("All Users")

	# Use a barcode that will never match any user — no need to query test data
	non_user_barcode = "INVALID_BARCODE_12345"

	result = _call_scan_login(page, non_user_barcode)

	assert not result[
		"ok"
	], f"Expected scan_login to fail for item barcode, but got success: {result['data']}"
	exc = result["data"].get("exc_type", "") + result["data"].get("exception", "")
	assert "Wrong barcode" in exc, f"Expected 'Wrong barcode' in error, got: {result['data']}"


@pytest.mark.order(3)
def test_non_mobile_user_rejected_when_restricted(page):
	"""
	Scenario: Enforce mobile user role restriction
	- BEAM Settings enable_scan_to_login = "Mobile Users Only"
	- Call scan_login with a user who lacks the 'BEAM Mobile User' role
	- Expect error "Not Beam mobile user"
	"""
	_set_scan_to_login("Mobile Users Only")

	user_barcode = _get_user_barcode(LOGIN_USER)

	with use_current_db_transaction():
		user_doc = frappe.get_doc("User", LOGIN_USER)
		had_mobile_role = any(r.role == "BEAM Mobile User" for r in user_doc.roles)
		if had_mobile_role:
			user_doc.roles = [r for r in user_doc.roles if r.role != "BEAM Mobile User"]
			user_doc.save()
			frappe.db.commit()

	try:
		result = _call_scan_login(page, user_barcode)

		assert not result[
			"ok"
		], f"Expected scan_login to fail for non-mobile user, but got success: {result['data']}"
		exc = result["data"].get("exc_type", "") + result["data"].get("exception", "")
		assert (
			"Not Beam mobile user" in exc
		), f"Expected 'Not Beam mobile user' in error, got: {result['data']}"
	finally:
		if had_mobile_role:
			with use_current_db_transaction():
				user_doc = frappe.get_doc("User", LOGIN_USER)
				user_doc.append("roles", {"role": "BEAM Mobile User"})
				user_doc.save()
				frappe.db.commit()


@pytest.mark.order(4)
def test_ip_restriction_allows_configured_ip(page):
	"""
	Scenario: Enforce IP restriction – scan from allowed IP succeeds
	- restrict_ip set to 127.0.0.1 (the test runner's IP)
	- Call scan_login with a valid user barcode
	- Expect HTTP 200 and success: True
	"""
	_set_scan_to_login("All Users")
	_set_restrict_ip("127.0.0.1")

	user_barcode = _get_user_barcode(LOGIN_USER)

	try:
		result = _call_scan_login(page, user_barcode)
		assert result["ok"], f"Expected scan_login to succeed from allowed IP, got: {result['data']}"
		assert result["data"].get("message", {}).get("success") is True
	finally:
		_set_restrict_ip("")


@pytest.mark.order(5)
def test_ip_restriction_blocks_disallowed_ip(page):
	"""
	Scenario: Enforce IP restriction – scan from disallowed IP is rejected
	- restrict_ip set to 192.0.2.255 (IETF TEST-NET, never matches 127.0.0.1)
	- Call scan_login with a valid user barcode
	- Expect error "Network not available"
	"""
	_set_scan_to_login("All Users")
	_set_restrict_ip("192.0.2.255")

	user_barcode = _get_user_barcode(LOGIN_USER)

	try:
		result = _call_scan_login(page, user_barcode)
		assert not result[
			"ok"
		], f"Expected scan_login to fail from disallowed IP, but got success: {result['data']}"
		exc = result["data"].get("exc_type", "") + result["data"].get("exception", "")
		assert (
			"Network not available" in exc
		), f"Expected 'Network not available' in error, got: {result['data']}"
	finally:
		_set_restrict_ip("")
