# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class BEAMSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		from beam.beam.doctype.beam_mobile_route.beam_mobile_route import BEAMMobileRoute
		from beam.beam.doctype.warehouse_types.warehouse_types import WarehouseTypes

		barcode_font_size: DF.Int
		company: DF.Link
		enable_demand: DF.Check
		enable_handling_units: DF.Check
		enable_scan_to_login: DF.Literal["Not Allowed", "Mobile Users Only", "All Users"]
		ignore_drop_shipped_items: DF.Check
		receiving_workstation: DF.Link | None
		restrict_ip: DF.SmallText | None
		routes: DF.Table[BEAMMobileRoute]
		scan_serial_no: DF.Check
		shipping_workstation: DF.Link | None
		show_scan_output: DF.Check
		warehouse_types: DF.TableMultiSelect[WarehouseTypes]
	# end: auto-generated types

	def onload(self):
		hooks = get_configuration_hooks()
		self.set_onload("components", hooks.components)
		self.set_onload("routes", hooks.routes)

	def get_beam_mobile_home_for_user(self, user):
		allowed_routes = []
		for row in self.routes:
			# if user has read permission on doctype
			allowed_routes.append(
				{
					"label": row.label,
					"route": row.route,
					"doctype": row.doctype,
				}
			)
		return {"routes": allowed_routes, "company": self.company}


@frappe.whitelist()
def create_beam_settings(company: str) -> str:
	beam_settings = frappe.new_doc("BEAM Settings")
	beam_settings.company = company
	beam_settings.auto_barcode_doctypes = '["Item", "Warehouse"]'
	beam_settings.save()
	return beam_settings


@frappe.whitelist()
def get_beam_home():
	# get user company via employee
	# get settings
	# apply roles
	user = frappe.session.user
	beam_settings = frappe.get_last_doc("BEAM Settings")
	return beam_settings.get_beam_mobile_home_for_user(user)


def get_configuration_hooks():
	bm = frappe.get_hooks().get("beam_mobile")
	components = sorted(list(set(bm.get("components").keys())))
	return frappe._dict({"components": components})


@frappe.whitelist()
def get_doctypes_with_item_barcodes() -> list[str]:
	"""Return all doctypes that have a Table field with options 'Item Barcode'."""
	existing_doctypes = set(frappe.get_all("DocType", pluck="name"))
	standard = frappe.get_all(
		"DocField",
		filters={"fieldtype": "Table", "options": "Item Barcode"},
		pluck="parent",
	)
	custom = frappe.get_all(
		"Custom Field",
		filters={"fieldtype": "Table", "options": "Item Barcode"},
		pluck="dt",
	)
	return sorted(existing_doctypes.intersection(standard + custom))
