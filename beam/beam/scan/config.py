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
		for key, values in hooked_frm.items():
			scannable_doctypes.add(key)
			[listview_doctypes.add(value) for value in values.keys()]

	for key, values in frm.items():
		scannable_doctypes.add(key)
		[frm_doctypes.add(value) for value in values.keys()]

	if hooked_frm:
		for key, values in hooked_frm.items():
			scannable_doctypes.add(key)
			[frm_doctypes.add(value) for value in values.keys()]

	return {
		"scannable_doctypes": list(scannable_doctypes),
		"listview": list(listview_doctypes),
		"frm": list(frm_doctypes),
		"client": beam_client,
	}
