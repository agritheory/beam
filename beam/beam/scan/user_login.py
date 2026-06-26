# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from erpnext import get_default_company
from frappe.auth import CookieManager
from frappe.core.doctype.user.user import get_restricted_ip_list

from beam.beam.scan import get_barcode_context


@frappe.whitelist(allow_guest=True)
def scan_login(barcode):
	client_ip = (
		frappe.local.request.headers.get("X-Forwarded-For") or frappe.local.request.remote_addr
	)

	user = get_barcode_context(barcode)
	if not user:
		frappe.throw("Wrong barcode", title="Login Error")

	if user["doc"].doctype != "User":
		frappe.throw("Wrong barcode", title="Login Error")

	user_doc = user["doc"]

	company = get_default_company()
	if not company:
		frappe.throw("Unable to determine company for login", title="Login Error")

	frappe.flags.ignore_permissions = True
	try:
		beam_settings = frappe.db.get_value(
			"BEAM Settings",
			{"company": company},
			["enable_scan_to_login", "restrict_ip"],
			as_dict=True,
		)
	finally:
		frappe.flags.ignore_permissions = False

	if not beam_settings:
		frappe.throw("BEAM Settings not found for company", title="Login Error")

	beam_settings = frappe._dict(beam_settings)

	if beam_settings.enable_scan_to_login == "Not Allowed":
		frappe.throw("Login scanning is not allowed", title="Scanner Login Disabled")

	ip_list = get_restricted_ip_list(beam_settings)
	if ip_list and not any(client_ip.startswith(ip) for ip in ip_list):
		frappe.throw("Network not available", title="Login Error")

	roles = [role.role for role in user_doc.get("roles")]
	if beam_settings.enable_scan_to_login == "Mobile Users Only" and "BEAM Mobile User" not in roles:
		frappe.throw("Not Beam mobile user", title="Login Error")

	try:
		if not getattr(frappe.local, "cookie_manager", None):
			frappe.local.cookie_manager = CookieManager()
		frappe.local.login_manager = frappe.auth.LoginManager()
		frappe.local.login_manager.user = user_doc.name
		frappe.local.login_manager.post_login()
	except Exception as e:
		frappe.throw(f"Error logging in: {str(e)}", title="Login Error")

	return {
		"success": True,
		"home_page": frappe.local.response.get("home_page"),
		"redirect_to": frappe.local.response.get("redirect_to"),
	}
