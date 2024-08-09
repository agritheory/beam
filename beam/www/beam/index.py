import frappe

no_cache = True


def get_context(context):
	csrf_token = frappe.sessions.get_csrf_token()
	context.csrf_token = csrf_token
	context.user = frappe.session.user
	frappe.db.commit()
