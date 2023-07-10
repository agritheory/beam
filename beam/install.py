import frappe


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
		if custom_field.dt == "Stock Entry Detail":
			frappe.set_value("Custom Field", custom_field, "read_only", 1)
		elif custom_field.dt == "Purchase Invoice Item":
			frappe.set_value("Custom Field", custom_field, "label", "Handling Unit")
		else:
			frappe.set_value("Custom Field", custom_field, "hidden", 1)
