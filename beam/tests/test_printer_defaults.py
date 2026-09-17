# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest

from beam.beam.printer_defaults import (
	SESSION_DEFAULT_KEY,
	add_network_printer_to_session_defaults,
	configured_printer,
	save_default_printer,
	seed_session_printer,
	set_session_printer,
	should_prefer_save_as_default,
	should_prefer_session_default,
)

TEST_USER = "Administrator"
KITCHEN_PRINTER = "Kitchen Printer"
RECEIVING_PRINTER = "Receiving Printer"


@pytest.fixture()
def printer_default_user():
	frappe.set_user("Administrator")
	original = frappe.db.get_value("User", TEST_USER, "default_network_printer_settings")
	frappe.defaults.clear_user_default(SESSION_DEFAULT_KEY, TEST_USER)
	yield TEST_USER
	frappe.set_user("Administrator")
	frappe.db.set_value("User", TEST_USER, "default_network_printer_settings", original)
	frappe.defaults.clear_user_default(SESSION_DEFAULT_KEY, TEST_USER)


@pytest.mark.order(107)
def test_configured_printer(printer_default_user):
	frappe.db.set_value("User", printer_default_user, "default_network_printer_settings", None)
	assert configured_printer(printer_default_user) is None

	frappe.db.set_value(
		"User", printer_default_user, "default_network_printer_settings", KITCHEN_PRINTER
	)
	assert configured_printer(printer_default_user) == KITCHEN_PRINTER

	frappe.db.set_value(
		"User", printer_default_user, "default_network_printer_settings", "Missing Printer"
	)
	assert configured_printer(printer_default_user) is None


@pytest.mark.order(108)
def test_seed_session_printer(printer_default_user):
	frappe.db.set_value("User", printer_default_user, "default_network_printer_settings", None)
	seed_session_printer(type("LoginManager", (), {"user": printer_default_user})())
	assert frappe.defaults.get_user_default(SESSION_DEFAULT_KEY, printer_default_user) is None

	frappe.db.set_value(
		"User", printer_default_user, "default_network_printer_settings", KITCHEN_PRINTER
	)
	seed_session_printer(type("LoginManager", (), {"user": printer_default_user})())
	assert (
		frappe.defaults.get_user_default(SESSION_DEFAULT_KEY, printer_default_user) == KITCHEN_PRINTER
	)


@pytest.mark.order(109)
def test_printer_default_preferences_and_persist(printer_default_user):
	frappe.db.set_value("User", printer_default_user, "default_network_printer_settings", None)
	assert should_prefer_save_as_default(KITCHEN_PRINTER, printer_default_user) is True
	assert should_prefer_session_default(KITCHEN_PRINTER, printer_default_user) is False

	frappe.db.set_value(
		"User", printer_default_user, "default_network_printer_settings", KITCHEN_PRINTER
	)
	assert should_prefer_save_as_default(KITCHEN_PRINTER, printer_default_user) is False
	assert should_prefer_session_default(RECEIVING_PRINTER, printer_default_user) is True
	assert should_prefer_session_default(KITCHEN_PRINTER, printer_default_user) is False

	frappe.set_user(printer_default_user)
	save_default_printer(RECEIVING_PRINTER)
	assert (
		frappe.db.get_value("User", printer_default_user, "default_network_printer_settings")
		== RECEIVING_PRINTER
	)
	assert frappe.defaults.get_user_default(SESSION_DEFAULT_KEY, printer_default_user) is None

	set_session_printer(KITCHEN_PRINTER)
	assert (
		frappe.db.get_value("User", printer_default_user, "default_network_printer_settings")
		== RECEIVING_PRINTER
	)
	assert (
		frappe.defaults.get_user_default(SESSION_DEFAULT_KEY, printer_default_user) == KITCHEN_PRINTER
	)

	add_network_printer_to_session_defaults()
	settings = frappe.get_single("Session Default Settings")
	matches = [
		row for row in settings.session_defaults if row.ref_doctype == "Network Printer Settings"
	]
	assert len(matches) == 1

	add_network_printer_to_session_defaults()
	settings.reload()
	matches = [
		row for row in settings.session_defaults if row.ref_doctype == "Network Printer Settings"
	]
	assert len(matches) == 1
