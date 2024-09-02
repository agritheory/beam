# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import frappe

no_cache = True


def get_context(context):
	csrf_token = frappe.sessions.get_csrf_token()
	context.csrf_token = csrf_token
	frappe.db.commit()
