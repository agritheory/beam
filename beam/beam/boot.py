# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import frappe

from beam.beam.scan.config import get_scan_doctypes


def boot_session(bootinfo):
	bootinfo.beam = get_scan_doctypes()
	bootinfo.beam["settings"] = get_beam_settings()
	bootinfo.beam["mass_uoms"] = get_mass_uoms()
	bootinfo.beam["scale_configs"] = get_scale_configs()
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


def get_mass_uoms():
	"""Get all UOMs that have a UOM Conversion Factor record with category='Mass'."""
	return frappe.get_all(
		"UOM Conversion Factor",
		filters={"category": "Mass"},
		pluck="from_uom",
		distinct=True,
	)


def get_scale_configs():
	"""Return scale_doctype_configs keyed by doctype_name."""
	configs = {}
	beam_settings_list = frappe.get_all(
		"BEAM Settings",
		fields=["name"],
	)
	for setting in beam_settings_list:
		scale_configs = frappe.get_all(
			"BEAM Scale Doctype Config",
			filters={"parent": setting.name},
			fields=[
				"doctype_name",
				"qty_field",
				"items_table_field",
				"zero_threshold",
				"autoadvance_on_zero",
			],
		)
		for config in scale_configs:
			configs[config.doctype_name] = {
				"qty_field": config.qty_field,
				"items_table_field": config.items_table_field,
				"zero_threshold": config.zero_threshold,
				"autoadvance_on_zero": config.autoadvance_on_zero,
			}
	return configs
