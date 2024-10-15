# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import uuid

import frappe
from frappe.model.document import Document


class HandlingUnit(Document):
	def autoname(self):
		self.handling_unit_name = self.name = str(uuid.uuid4().int >> 64)

	def validate(self):
		barcode = frappe.new_doc("Item Barcode")
		barcode.parenttype = "Handling Unit"
		barcode.barcode_type = "Code128"
		barcode.barcode = self.name
		barcode.parent = self.name
		barcode.flags.ignore_permissions = True
		barcode.save()
