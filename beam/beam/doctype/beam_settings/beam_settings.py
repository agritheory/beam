# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class BEAMSettings(Document):
	pass


@frappe.whitelist()
def create_beam_settings(company: str) -> str:
	beams = frappe.new_doc("BEAM Settings")
	beams.company = company
	beams.save()
	return beams
