# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import frappe

from beam.beam.scan import frm, listview


@frappe.whitelist()
@frappe.read_only()
def get_scan_doctypes():
	scannable_doctypes = set()
	listview_doctypes = set()
	frm_doctypes = set()
	hooked_listview = frappe.get_hooks("beam_listview")
	hooked_frm = frappe.get_hooks("beam_frm")
	beam_client = frappe.get_hooks("beam_client")

	for key, values in listview.items():
		scannable_doctypes.add(key)
		[listview_doctypes.add(value) for value in values.keys()]

	if hooked_listview:
		for key, values in hooked_listview.items():
			scannable_doctypes.add(key)
			[listview_doctypes.add(value) for value in values.keys()]

	for key, values in frm.items():
		scannable_doctypes.add(key)
		[frm_doctypes.add(value) for value in values.keys()]

	if hooked_frm:
		for key, values in hooked_frm.items():
			scannable_doctypes.add(key)
			[frm_doctypes.add(value) for value in values.keys()]

	# TODO: should this be filtered against a specific company?
	_scan_last = frappe.get_all("BEAM Settings", fields=["show_scan_output"])
	scan_last = _scan_last[0] if _scan_last else {"show_scan_output": False}

	return {
		"scannable_doctypes": list(scannable_doctypes),
		"listview": list(listview_doctypes),
		"frm": list(frm_doctypes),
		"client": beam_client,
		**scan_last,
	}
