# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

from typing import TYPE_CHECKING

import frappe
from frappe.model.document import Document


class BEAMSettings(Document):
	if TYPE_CHECKING:
		from frappe.types import DF

		enable_scan_to_login: DF.Literal["Not Allowed", "Mobile Users Only", "All Users"]
		restrict_ip: DF.SmallText | None


@frappe.whitelist()
def create_beam_settings(company: str) -> str:
	beams = frappe.new_doc("BEAM Settings")
	beams.company = company
	beams.auto_barcode_doctypes = '["Item", "Warehouse", "User"]'
	beams.save()
	return beams


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
