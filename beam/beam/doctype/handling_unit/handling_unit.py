# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import uuid

import frappe
from frappe.model.document import Document


class HandlingUnit(Document):
	# begin: auto-generated types
	# This code is auto-generated. Do not modify anything in this block.

	from typing import TYPE_CHECKING

	if TYPE_CHECKING:
		from frappe.types import DF

		handling_unit_name: DF.Data | None
	# end: auto-generated types

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
