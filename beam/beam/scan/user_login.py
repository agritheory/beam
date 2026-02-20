# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from erpnext import get_default_company
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

	# employee = frappe.get_doc("Employee", {"user_id": user["doc"].name})
	employee_name = frappe.db.get_value(
		"Employee",
		{"user_id": user["doc"].name},
		"name",
	)
	if not employee_name:
		frappe.throw("Employee not found", title="Login Error")

	employee = frappe.get_doc("Employee", employee_name)
	company = employee.company or get_default_company()

	BEAMSettings = frappe.get_doc("BEAM Settings", {"company": company})
	if BEAMSettings.enable_scan_to_login == "Not Allowed":
		frappe.throw("Login scanning is not allowed", title="Scanner Login Disabled")

	ip_list = get_restricted_ip_list(BEAMSettings)
	if ip_list and not any(client_ip.startswith(ip) for ip in ip_list):
		frappe.throw("Network not available", title="Login Error")

	user_doc = frappe.get_doc("User", user["doc"].name)
	roles = [role.role for role in user_doc.get("roles")]
	if BEAMSettings.enable_scan_to_login == "Mobile Users Only" and not "BEAM Mobile User" in roles:
		frappe.throw("Not Beam mobile user", title="Login Error")

	try:
		frappe.local.login_manager = frappe.auth.LoginManager()
		frappe.local.login_manager.user = user_doc.name
		frappe.local.login_manager.post_login()
	except Exception as e:
		frappe.throw(f"Error logging in: {str(e)}", title="Login Error")

	return {"success": True, "message": f"User {user_doc.name} logged in successfully"}
