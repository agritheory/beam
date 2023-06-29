import frappe


def after_install():
	print("Setting up Inventory Dimension")
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

	# hide target fields - not applicable to handling units
	for custom_field in frappe.get_all("Custom Field", {"label": "Target Handling Unit"}):
		frappe.set_value("Custom Field", custom_field, "hidden", 1)

	# hide on Job Card, maybe others also
