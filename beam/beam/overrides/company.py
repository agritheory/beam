# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe

from beam.beam.doctype.beam_settings.beam_settings import create_beam_settings


def create_company_beam_settings(doc, method=None):
	if not frappe.db.exists("BEAM Settings", {"company": doc.name}):
		create_beam_settings(doc.name)
