# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import os

import frappe
from erpnext import get_default_company

from beam.beam.doctype.beam_settings.beam_settings import create_beam_settings


def reload_beam_doctypes():
	"""Sync BEAM DocTypes from app JSON before patches touch BEAM Settings.

	If a child DocType is missing from tabDocType, Frappe defaults the module to
	Core and import fails (frappe.core.doctype.*).
	"""
	doctype_dir = os.path.join(frappe.get_app_path("beam"), "beam", "doctype")
	for folder in sorted(os.listdir(doctype_dir)):
		path = os.path.join(doctype_dir, folder)
		if os.path.isfile(os.path.join(path, f"{folder}.json")):
			frappe.reload_doc("beam", "doctype", folder)


def execute(company=None):
	reload_beam_doctypes()

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
			continue
		for row in default_config:
			doc.append("routes", row)
		doc.save()
