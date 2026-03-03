# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import frappe

from beam.beam.scan.config import get_scan_doctypes


def boot_session(bootinfo):
	bootinfo.beam = get_scan_doctypes()
	bootinfo.beam["settings"] = get_beam_settings()
	bootinfo.beam["default_hu_print_format"] = frappe.get_meta("Handling Unit").get(
		"default_print_format"
	)


def get_beam_settings():
	"""Get BEAM Settings for all companies, keyed by company name."""
	settings = {}
	beam_settings = frappe.get_all(
		"BEAM Settings",
		fields=["company", "enable_handling_units"],
	)
	for setting in beam_settings:
		settings[setting.company] = {
			"enable_handling_units": setting.enable_handling_units,
		}
	return settings


def redirect_to_beam():
	user_roles = frappe.get_all(
		"Has Role", fields=["role"], filters={"parent": frappe.session.user}, pluck="role"
	)
	if "BEAM Mobile User" in user_roles:
		frappe.local.response["home_page"] = "/beam#/"
