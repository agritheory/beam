# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt
import frappe

from beam.beam.scan.config import get_scan_doctypes


def boot_session(bootinfo):
	bootinfo.beam = get_scan_doctypes()


def redirect_to_beam():
	user_agent = frappe.request.headers.get("User-Agent", "").lower()
	if any(agent in user_agent for agent in ["iphone", "android", "blackberry", "ipad", "mobile"]):
		frappe.local.response["home_page"] = "/beam/"
