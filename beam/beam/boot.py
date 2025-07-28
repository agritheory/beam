# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import frappe

from beam.beam.scan.config import get_scan_doctypes


def boot_session(bootinfo):
	bootinfo.beam = get_scan_doctypes()
	bootinfo.enabled_beam_settings = frappe.get_all(
		"BEAM Settings",
		filters={"enable_demand": True},
		pluck="name",
	)


def redirect_to_beam():
	user_roles = frappe.get_roles(frappe.session.user)

	if "BEAM Mobile User" in user_roles:
		frappe.local.response["home_page"] = "/beam#/"
