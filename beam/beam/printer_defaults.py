# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import frappe

NPS_DOCTYPE = "Network Printer Settings"
SESSION_DEFAULT_KEY = frappe.scrub(NPS_DOCTYPE)


def configured_printer(user=None):
	user = user or frappe.session.user
	if user == "Guest":
		return None

	printer = frappe.db.get_value("User", user, "default_network_printer_settings")
	if not printer:
		return None
	if frappe.db.exists(NPS_DOCTYPE, printer):
		return printer
	return None


def seed_session_printer(login_manager=None):
	user = login_manager.user if login_manager else frappe.session.user
	if user == "Guest":
		return

	printer = configured_printer(user)
	if printer:
		frappe.defaults.set_user_default(SESSION_DEFAULT_KEY, printer, user)


def should_prefer_save_as_default(selected, user=None):
	if not selected:
		return False
	return not configured_printer(user)


def should_prefer_session_default(selected, user=None):
	if not selected:
		return False
	configured = configured_printer(user)
	if not configured:
		return False
	return selected != configured


def validate_printer_setting(printer_setting):
	if not printer_setting or not frappe.db.exists(NPS_DOCTYPE, printer_setting):
		frappe.throw(frappe._("Invalid Network Printer Settings"))


@frappe.whitelist()
def save_default_printer(printer_setting):
	validate_printer_setting(printer_setting)
	user = frappe.get_doc("User", frappe.session.user)
	user.default_network_printer_settings = printer_setting
	user.save(ignore_permissions=True)
	return printer_setting


@frappe.whitelist()
def set_session_printer(printer_setting):
	validate_printer_setting(printer_setting)
	frappe.defaults.set_user_default(SESSION_DEFAULT_KEY, printer_setting)
	return printer_setting


def add_network_printer_to_session_defaults():
	settings = frappe.get_single("Session Default Settings")
	for row in settings.session_defaults:
		if row.ref_doctype == NPS_DOCTYPE:
			return
	settings.append("session_defaults", {"ref_doctype": NPS_DOCTYPE})
	settings.save(ignore_permissions=True)
