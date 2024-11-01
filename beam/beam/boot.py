# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt
import frappe

from beam.beam.scan.config import get_scan_doctypes


def boot_session(bootinfo):
	bootinfo.beam = get_scan_doctypes()


def redirect_to_beam():
	user_agent = frappe.request.headers.get("User-Agent", "").lower()
	mobile_keywords = [
		"android",
		"webos",
		"iphone",
		"ipad",
		"ipod",
		"blackberry",
		"iemobile",
		"opera mini",
		"mobile",
	]
	if any(agent in user_agent for agent in mobile_keywords):
		frappe.local.response["home_page"] = "/beam/"
