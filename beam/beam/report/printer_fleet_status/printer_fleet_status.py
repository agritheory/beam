# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe import _

from beam.beam.overrides.network_printer_settings import get_fleet_status


def execute(filters=None):
	filters = frappe._dict(filters or {})
	columns = get_columns()
	data = get_fleet_status(filters.get("server_ip"))
	return columns, data


def get_columns():
	return [
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 140},
		{"label": _("Server IP"), "fieldname": "server_ip", "fieldtype": "Data", "width": 120},
		{"label": _("Port"), "fieldname": "port", "fieldtype": "Int", "width": 70},
		{"label": _("CUPS Queue"), "fieldname": "cups_queue", "fieldtype": "Data", "width": 140},
		{
			"label": _("Network Printer Settings"),
			"fieldname": "nps_name",
			"fieldtype": "Link",
			"options": "Network Printer Settings",
			"width": 180,
		},
		{"label": _("CUPS Location"), "fieldname": "cups_location", "fieldtype": "Data", "width": 160},
		{
			"label": _("ERPNext Location"),
			"fieldname": "erpnext_location",
			"fieldtype": "Data",
			"width": 160,
		},
		{
			"label": _("CUPS Device URI"),
			"fieldname": "cups_device_uri",
			"fieldtype": "Data",
			"width": 220,
		},
		{
			"label": _("ERPNext Device URI"),
			"fieldname": "erpnext_device_uri",
			"fieldtype": "Data",
			"width": 220,
		},
		{"label": _("Accepting Jobs"), "fieldname": "accepting_jobs", "fieldtype": "Data", "width": 110},
		{"label": _("Printer State"), "fieldname": "printer_state", "fieldtype": "Data", "width": 120},
	]
