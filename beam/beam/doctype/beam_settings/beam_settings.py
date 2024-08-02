# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class BEAMSettings(Document):
	pass


@frappe.whitelist()
def get_beam_settings(company: str) -> str:
	if frappe.db.exists("BEAM Settings", {"company": company}):
		return frappe.get_doc("BEAM Settings", {"company": company})
	settings = frappe.new_doc("BEAM Settings")
	settings.company = company
	settings.save()
	return settings
