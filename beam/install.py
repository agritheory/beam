# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

from beam.beam.inventory_dimension import setup_inventory_dimensions


def create_beam_mobile_user_role():
	if not frappe.db.exists("Role", "BEAM Mobile User"):
		role = frappe.get_doc(
			{"doctype": "Role", "role_name": "BEAM Mobile User", "desk_access": 0, "home_page": "/app"}
		)
		role.insert(ignore_permissions=True)


def after_install():
	setup_inventory_dimensions(
		[{"dimension_name": "Handling Unit", "reference_document": "Handling Unit"}]
	)
