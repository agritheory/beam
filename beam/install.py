import frappe

from beam.beam.scan.config import get_scan_doctypes


def after_install():
	print("Setting up Handling Unit Inventory Dimension")
	if frappe.db.exists("Inventory Dimension", "Handling Unit"):
		return
	huid = frappe.new_doc("Inventory Dimension")
	huid.dimension_name = "Handling Unit"
	huid.reference_document = "Handling Unit"
	huid.apply_to_all_doctypes = 1
	huid.save()

	# re-label
	for custom_field in frappe.get_all("Custom Field", {"label": "Source Handling Unit"}):
		frappe.set_value("Custom Field", custom_field, "label", "Handling Unit")

	# hide target fields
	for custom_field in frappe.get_all(
		"Custom Field", {"label": "Target Handling Unit"}, ["name", "dt"]
	):
		if custom_field.dt == "Purchase Invoice Item":
			frappe.set_value("Custom Field", custom_field, "label", "Handling Unit")
		else:
<<<<<<< HEAD
			frappe.set_value("Custom Field", custom_field, "read_only", 1)
=======
			frappe.set_value("Custom Field", custom_field, "hidden", 1)

	frm_doctypes = get_scan_doctypes()["frm"]

	for custom_field in frappe.get_all("Custom Field", {"label": "Handling Unit"}, ["name", "dt"]):
		frappe.set_value("Custom Field", custom_field["name"], "no_copy", 1)

		if (
			custom_field["dt"] not in frm_doctypes
			and custom_field["dt"].replace(" Item", "").replace(" Detail", "") not in frm_doctypes
		):
			frappe.set_value("Custom Field", custom_field["name"], "hidden", 1)
>>>>>>> ac62bd8 (feat: no copy for hu fields, hide hu field based configured doctypes)
