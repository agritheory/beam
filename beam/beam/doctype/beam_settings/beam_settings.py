# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class BEAMSettings(Document):
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
	# routes = sorted(list(set([p.get('path') for p in bm.get('routes')])))
	return frappe._dict({"components": components})
