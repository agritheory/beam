# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.printing.doctype.network_printer_settings.network_printer_settings import (
	NetworkPrinterSettings,
)


class BEAMNetworkPrinterSettings(NetworkPrinterSettings):
	@frappe.whitelist()
	def get_printers_list(self, ip="127.0.0.1", port=631):
		printer_list = []
		try:
			import cups
		except ImportError:
			frappe.throw(
				_(
					"""This feature can not be used as dependencies are missing.
				Please contact your system manager to enable this by installing pycups!"""
				)
			)
			return
		try:
			cups.setServer(self.server_ip)
			cups.setPort(self.port)
			conn = cups.Connection()
			printers = conn.getPrinters()
			for printer_id, printer in printers.items():
				make_model = printer["printer-make-and-model"]
				location = printer.get("printer-location", "")
				description = f"{make_model}, {location}" if location else make_model
				printer_list.append(
					{
						"value": printer_id,
						"label": printer_id,
						"description": description,
						"location": location,
					}
				)
		except RuntimeError:
			frappe.throw(_("Failed to connect to server"))
		except frappe.ValidationError:
			frappe.throw(_("Failed to connect to server"))
		return printer_list

	def validate(self):
		self.push_location_to_cups()

	def push_location_to_cups(self):
		if not self.printer_name:
			return
		try:
			import cups

			cups.setServer(self.server_ip)
			cups.setPort(self.port)
			conn = cups.Connection()
			conn.setPrinterLocation(self.printer_name, self.printer_location or "")
		except Exception:
			pass
