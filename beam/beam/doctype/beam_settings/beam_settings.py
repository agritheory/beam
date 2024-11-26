# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class BEAMSettings(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from beam.beam.doctype.beam_mobile_route.beam_mobile_route import BEAMMobileRoute
		from beam.beam.doctype.warehouse_types.warehouse_types import WarehouseTypes
		from frappe.types import DF

		barcode_font_size: DF.Int
		company: DF.Link
		enable_demand: DF.Check
		enable_handling_units: DF.Check
		ignore_drop_shipped_items: DF.Check
		receiving_workstation: DF.Link | None
		routes: DF.Table[BEAMMobileRoute]
		shipping_workstation: DF.Link | None
		warehouse_types: DF.TableMultiSelect[WarehouseTypes]
	# end: auto-generated types

	def onload(self):
		hooks = get_configuration_hooks()
		self.set_onload("components", hooks.components)
		self.set_onload("routes", hooks.routes)

	def validate(self):
		# adding a label check since multiple paths can use the Demand component
		existing_demand_route = [
			route for route in self.routes if route.label == "Demand" and route.component == "Demand"
		]

		if self.enable_demand:
			# add demand route into mobile list
			if not existing_demand_route:
				self.append(
					"routes",
					{
						"component": "Demand",
						"dt": "Stock Entry",
						"label": "Demand",
						"route": "#/demand",
					},
				)
		else:
			# remove demand route from mobile list
			if existing_demand_route:
				self.remove(existing_demand_route[0])

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
