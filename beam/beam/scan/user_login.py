import frappe
from beam.beam.scan import get_barcode_context


@frappe.whitelist(allow_guest=True)
def scan_login(barcode):
	client_ip = (
		frappe.local.request.headers.get("X-Forwarded-For") or frappe.local.request.remote_addr
	)
	print(f"Barcode: {barcode}, IP: {client_ip}")

	user = get_barcode_context(barcode)
	if not user:
		frappe.throw("Wrong barcode", title="Login Error")

	if user["doc"].doctype != "User":
		frappe.throw("Wrong barcode", title="Login Error")

	user_doc = frappe.get_doc("User", user["doc"].name)
	if not user_doc:
		frappe.throw("User doesn't exist", title="Login Error")

	roles = [role.role for role in user_doc.get("roles")]
	if not "BEAM Mobile User" in roles:
		frappe.throw("Not Beam mobile user", title="Login Error")

	try:
		frappe.local.login_manager = frappe.auth.LoginManager()
		frappe.local.login_manager.user = user_doc.name
		frappe.local.login_manager.post_login()  # Crear sesión activa
	except Exception as e:
		frappe.throw(f"Error logging in: {str(e)}", title="Login Error")

	return {"success": True, "message": f"User {user_doc.name} logged in successfully"}
