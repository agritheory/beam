# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from erpnext import get_default_company

from beam.beam.doctype.beam_settings.beam_settings import create_beam_settings


def execute(company=None):
	frappe.reload_doc("beam", "doctype", "beam_settings")

	default_config = [
		{
			"label": "Manufacture",
			"route": "#/manufacture",
			"dt": "Stock Entry",
			"component": "Manufacture",
		},
		{"label": "Demand", "route": "#/demand", "dt": "Stock Entry", "component": "Demand"},
		{"label": "Move", "route": "#/move", "dt": "Stock Entry", "component": "Demand"},
		{"label": "Receive", "route": "#/receive", "dt": "Purchase Receipt", "component": "Receive"},
		{"label": "Ship", "route": "#/ship", "dt": "Delivery Note", "component": "Ship"},
		{"label": "Repack", "route": "#/repack", "dt": "Stock Entry", "component": "Repack"},
	]

	beam_configs = frappe.get_all("BEAM Settings", pluck="name")
	if not beam_configs:
		company = get_default_company() or company
		if not company:
			return
		beam_configs = [create_beam_settings(company)]
	for company in beam_configs:
		doc = frappe.get_doc("BEAM Settings", company)
		if len(doc.routes) > 0:
			return
		for row in default_config:
			doc.append("routes", row)
		doc.save()
