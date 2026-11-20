# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import os

import frappe


def execute():
	custom_path = os.path.join(frappe.get_app_path("beam"), "beam", "custom", "workstation.json")
	if not os.path.isfile(custom_path):
		return
	from frappe.modules.import_file import import_file_by_path

	import_file_by_path(custom_path, force=True)
