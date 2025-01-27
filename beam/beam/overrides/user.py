# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

from frappe.core.doctype.user.user import User
from beam.beam.barcodes import create_beam_barcode


class BEAMUser(User):
	def validate(self):
		super().validate()
		create_beam_barcode(self)
