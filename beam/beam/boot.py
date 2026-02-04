# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import frappe

from beam.beam.scan.config import get_scan_doctypes


def boot_session(bootinfo):
	bootinfo.beam = get_scan_doctypes()
	bootinfo.beam["settings"] = get_beam_settings()
	bootinfo.beam["default_hu_print_format"] = get_handling_unit_default_print_format()


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


def get_handling_unit_default_print_format():
	"""Get the default print format for Handling Unit doctype."""
	return frappe.db.get_value("DocType", "Handling Unit", "default_print_format")
