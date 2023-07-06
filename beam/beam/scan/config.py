import frappe

from beam.beam.scan import frm, listview


@frappe.whitelist()
def get_scan_doctypes():
	scannable_doctypes = set()
	listview_doctypes = set()
	frm_doctypes = set()
	hooked_listview = frappe.get_hooks("beam_listview")
	hooked_frm = frappe.get_hooks("beam_frm")

	for key, values in listview.items() + hooked_listview.items():
		scannable_doctypes.add(key)
		listview_doctypes.add(values.keys())

	print(scannable_doctypes, listview_doctypes)
