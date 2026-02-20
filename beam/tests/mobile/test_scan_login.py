# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest
from playwright.sync_api import expect

from beam.tests.test_utils import use_current_db_transaction

BASE_URL = "http://127.0.0.1:8000"
LOGIN_URL = f"{BASE_URL}/login"
HOME_URL = "/beam"


def set_scan_mode(mode: str):
	with use_current_db_transaction():
		settings = frappe.get_doc("BEAM Settings", "Ambrosia Pie Company")
		settings.enable_scan_to_login = mode
		settings.save()


def set_ip_restriction(ip_list=None):
	with use_current_db_transaction():
		settings = frappe.get_doc("BEAM Settings", "Ambrosia Pie Company")
		settings.restrict_ip = "\n".join(ip_list or [])
		settings.save()


def get_valid_user():
	rows = frappe.get_all(
		"Item Barcode",
		filters={"parenttype": "User"},
		fields=["parent", "barcode"],
		limit=1,
	)

	if not rows:
		raise Exception("No users with barcode found")

	return {
		"user": rows[0].parent,
		"barcode": rows[0].barcode,
	}


# -------------------------------------------------------
# 1️⃣ SUCCESS LOGIN
# -------------------------------------------------------
@pytest.mark.order(1)
def test_scan_login_success(page):
	set_scan_mode("All Users")

	page.goto(LOGIN_URL)

	# wait until scan handler ready
	page.wait_for_function("window.__beam_test_scan !== undefined")

	user = get_valid_user()

	page.evaluate(
		"barcode => window.__beam_test_scan(barcode)",
		user["barcode"],
	)

	page.wait_for_url("**/beam")
	expect(page).to_have_url(lambda url: HOME_URL in url)


# -------------------------------------------------------
# 2️⃣ INVALID BARCODE
# -------------------------------------------------------
@pytest.mark.order(2)
def test_invalid_barcode(page):
	set_scan_mode("All Users")

	page.goto(LOGIN_URL)
	page.wait_for_function("window.__beam_test_scan !== undefined")

	page.evaluate(
		"barcode => window.__beam_test_scan(barcode)",
		"INVALID123",
	)

	page.wait_for_timeout(800)

	expect(page.get_by_text("Wrong barcode")).to_be_visible()
	expect(page).to_have_url(lambda url: "/login" in url)


# -------------------------------------------------------
# 3️⃣ MOBILE USER ONLY
# -------------------------------------------------------
@pytest.mark.order(3)
def test_mobile_user_only_restriction(page):
	set_scan_mode("Mobile Users Only")

	page.goto(LOGIN_URL)
	page.wait_for_function("window.__beam_test_scan !== undefined")

	with use_current_db_transaction():
		users = frappe.get_all(
			"User",
			filters={"enabled": 1},
			fields=["name"],
		)

		target_barcode = None

		for u in users:
			rows = frappe.get_all(
				"Item Barcode",
				filters={"parent": u.name, "parenttype": "User"},
				fields=["barcode"],
				limit=1,
			)

			if not rows:
				continue

			if not frappe.db.exists("Employee", {"user_id": u.name}):
				continue

			has_role = frappe.db.exists(
				"Has Role",
				{"parent": u.name, "role": "BEAM Mobile User"},
			)

			if not has_role:
				target_barcode = rows[0].barcode
				break

		assert target_barcode, "Need user without BEAM Mobile User role"

	page.evaluate(
		"barcode => window.__beam_test_scan(barcode)",
		target_barcode,
	)

	page.wait_for_timeout(800)

	expect(page.get_by_text("Not Beam mobile user")).to_be_visible()
	expect(page).to_have_url(lambda url: "/login" in url)


# -------------------------------------------------------
# 4️⃣ IP RESTRICTION
# -------------------------------------------------------
@pytest.mark.order(4)
def test_ip_restriction(page):
	set_scan_mode("All Users")

	user = get_valid_user()
	barcode = user["barcode"]

	# allow IP
	set_ip_restriction(["127.0.0.1"])

	page.goto(LOGIN_URL)
	page.wait_for_function("window.__beam_test_scan !== undefined")

	page.evaluate(
		"barcode => window.__beam_test_scan(barcode)",
		barcode,
	)

	page.wait_for_url("**/beam")
	expect(page).to_have_url(lambda url: HOME_URL in url)

	# logout
	page.goto("/logout")
	page.goto(LOGIN_URL)
	page.wait_for_function("window.__beam_test_scan !== undefined")

	# block IP
	set_ip_restriction(["192.168.1.1"])

	page.evaluate(
		"barcode => window.__beam_test_scan(barcode)",
		barcode,
	)

	page.wait_for_timeout(800)

	expect(page.get_by_text("Network not available")).to_be_visible()
	expect(page).to_have_url(lambda url: "/login" in url)


# -------------------------------------------------------
# 5️⃣ SCAN DISABLED
# -------------------------------------------------------
@pytest.mark.order(5)
def test_scan_login_disabled(page):
	set_scan_mode("Not Allowed")

	page.goto(LOGIN_URL)
	page.wait_for_function("window.__beam_test_scan !== undefined")

	user = get_valid_user()

	page.evaluate(
		"barcode => window.__beam_test_scan(barcode)",
		user["barcode"],
	)

	page.wait_for_timeout(800)

	expect(page.get_by_text("Login scanning is not allowed")).to_be_visible()
	expect(page).to_have_url(lambda url: "/login" in url)
