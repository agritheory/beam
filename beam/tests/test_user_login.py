# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

from unittest.mock import MagicMock

import frappe
import pytest
from frappe.auth import CookieManager

from erpnext import get_default_company
from beam.beam.barcodes import create_beam_barcode
from beam.install import create_beam_mobile_user_role


TEST_USER_EMAIL = "scan_login_test@example.com"


@pytest.fixture()
def beam_settings():
	company = get_default_company()
	settings = frappe.get_doc("BEAM Settings", {"company": company})
	original_enable = settings.enable_scan_to_login
	original_restrict_ip = settings.restrict_ip
	yield settings
	frappe.set_user("Administrator")
	settings.enable_scan_to_login = original_enable
	settings.restrict_ip = original_restrict_ip
	settings.save()


@pytest.fixture()
def scan_login_user(beam_settings):
	create_beam_mobile_user_role()
	beam_settings.auto_barcode_doctypes = '["Item", "Warehouse", "User"]'
	beam_settings.save()

	if frappe.db.exists("User", TEST_USER_EMAIL):
		frappe.delete_doc("User", TEST_USER_EMAIL, force=1)

	user = frappe.new_doc("User")
	user.email = TEST_USER_EMAIL
	user.first_name = "Scan"
	user.last_name = "Login"
	user.send_welcome_email = 0
	user.new_password = "ScanLogin1!Test2024"
	user.flags.ignore_password_policy = True
	user.append("roles", {"role": "Stock User"})
	user.save()

	user.reload()
	create_beam_barcode(user)
	user.save()

	barcode = next(b.barcode for b in user.barcodes if b.barcode_type == "Code128")

	yield {"user": user, "barcode": barcode}

	frappe.set_user("Administrator")
	if frappe.db.exists("User", TEST_USER_EMAIL):
		frappe.delete_doc("User", TEST_USER_EMAIL, force=1)


@pytest.fixture()
def mock_request_ip():
	original_request = getattr(frappe.local, "request", None)
	original_cookie_manager = getattr(frappe.local, "cookie_manager", None)
	mock_request = MagicMock()
	mock_request.headers = MagicMock()
	mock_request.headers.get = lambda key: "127.0.0.1" if key == "X-Forwarded-For" else None
	mock_request.remote_addr = "127.0.0.1"
	mock_request.path = "/api/method/beam.beam.scan.user_login.scan_login"
	frappe.local.request = mock_request
	frappe.local.cookie_manager = CookieManager()
	yield mock_request
	if original_request is not None:
		frappe.local.request = original_request
	if original_cookie_manager is not None:
		frappe.local.cookie_manager = original_cookie_manager


def test_scan_login_rejects_when_not_allowed(beam_settings, scan_login_user, mock_request_ip):
	beam_settings.enable_scan_to_login = "Not Allowed"
	beam_settings.save()

	frappe.set_user("Guest")
	with pytest.raises(frappe.ValidationError, match="Login scanning is not allowed"):
		frappe.call("beam.beam.scan.user_login.scan_login", barcode=scan_login_user["barcode"])


def test_scan_login_rejects_invalid_barcode(beam_settings, mock_request_ip):
	beam_settings.enable_scan_to_login = "All Users"
	beam_settings.save()

	frappe.set_user("Guest")
	with pytest.raises(frappe.ValidationError, match="Wrong barcode"):
		frappe.call("beam.beam.scan.user_login.scan_login", barcode="00000000000000000000")


def test_scan_login_succeeds_for_all_users(beam_settings, scan_login_user, mock_request_ip):
	beam_settings.enable_scan_to_login = "All Users"
	beam_settings.save()

	frappe.set_user("Guest")
	result = frappe.call("beam.beam.scan.user_login.scan_login", barcode=scan_login_user["barcode"])

	assert result["success"] is True
	assert result.get("home_page") or result.get("redirect_to")
	frappe.set_user("Administrator")


def test_scan_login_rejects_non_mobile_user(beam_settings, scan_login_user, mock_request_ip):
	beam_settings.enable_scan_to_login = "Mobile Users Only"
	beam_settings.save()

	frappe.set_user("Guest")
	with pytest.raises(frappe.ValidationError, match="Not Beam mobile user"):
		frappe.call("beam.beam.scan.user_login.scan_login", barcode=scan_login_user["barcode"])


def test_scan_login_succeeds_for_mobile_user(beam_settings, scan_login_user, mock_request_ip):
	beam_settings.enable_scan_to_login = "Mobile Users Only"
	beam_settings.save()

	user = frappe.get_doc("User", scan_login_user["user"].name)
	user.append("roles", {"role": "BEAM Mobile User"})
	user.save()

	frappe.set_user("Guest")
	result = frappe.call("beam.beam.scan.user_login.scan_login", barcode=scan_login_user["barcode"])

	assert result["success"] is True
	assert result.get("home_page") or result.get("redirect_to")
	frappe.set_user("Administrator")


def test_scan_login_blocks_disallowed_ip(beam_settings, scan_login_user, mock_request_ip):
	beam_settings.enable_scan_to_login = "All Users"
	beam_settings.restrict_ip = "10.0.0.1"
	beam_settings.save()

	frappe.set_user("Guest")
	with pytest.raises(frappe.ValidationError, match="Network not available"):
		frappe.call("beam.beam.scan.user_login.scan_login", barcode=scan_login_user["barcode"])


def test_scan_login_allows_restricted_ip(beam_settings, scan_login_user, mock_request_ip):
	beam_settings.enable_scan_to_login = "All Users"
	beam_settings.restrict_ip = "127.0.0.1"
	beam_settings.save()

	frappe.set_user("Guest")
	result = frappe.call("beam.beam.scan.user_login.scan_login", barcode=scan_login_user["barcode"])

	assert result["success"] is True
	frappe.set_user("Administrator")
