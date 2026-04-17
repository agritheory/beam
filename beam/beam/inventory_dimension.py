# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import frappe

from beam.beam.scan.config import get_scan_doctypes


def setup_inventory_dimensions(inv_dim_dict_list: list[dict]) -> None:
	"""Create Inventory Dimensions and perform supporting setup.

	Each dictionary in the list should contain the following keys:
	  dimension_name      - required
	  reference_document  - required
	  target_fieldname    - optional
	  apply_to_all_doctypes - optional, defaults to 1
	  custom_carry_forward  - optional, defaults to 0

	Side-effects per dimension:
	  - Relabels ``Source {Name}`` custom fields to ``{Name}``.
	  - Hides / marks read-only ``Target {Name}`` custom fields (keeps Purchase Invoice Item
	    variant visible and relabeled).
	  - Sets ``no_copy`` on all generated custom fields and marks them read-only on doctypes that
	    aren't scannable form targets (based on BEAM's ``get_scan_doctypes``).
	"""
	frappe.flags.in_test = True
	for inv_dim_dict in inv_dim_dict_list:
		name = inv_dim_dict["dimension_name"]
		print(f"Setting up {name} Inventory Dimension")
		if frappe.db.exists("Inventory Dimension", name):
			continue

		inv_dim_dict.setdefault("apply_to_all_doctypes", 1)
		inv_dim = frappe.new_doc("Inventory Dimension")
		inv_dim.update(inv_dim_dict)
		inv_dim.save()

		for custom_field in frappe.get_all("Custom Field", {"label": f"Source {name}"}):
			frappe.set_value("Custom Field", custom_field, "label", name)

		for custom_field in frappe.get_all("Custom Field", {"label": f"Target {name}"}, ["name", "dt"]):
			if custom_field.dt == "Purchase Invoice Item":
				frappe.set_value("Custom Field", custom_field, "label", name)
			else:
				frappe.set_value("Custom Field", custom_field, "read_only", 1)
				frappe.set_value("Custom Field", custom_field["name"], "no_copy", 1)

		frm_doctypes = get_scan_doctypes()["frm"]

		for custom_field in frappe.get_all("Custom Field", {"label": name}, ["name", "dt"]):
			frappe.set_value("Custom Field", custom_field["name"], "no_copy", 1)

			if (
				custom_field["dt"] not in frm_doctypes
				and custom_field["dt"].replace(" Item", "").replace(" Detail", "") not in frm_doctypes
			):
				frappe.set_value("Custom Field", custom_field["name"], "read_only", 1)
				frappe.set_value("Custom Field", custom_field["name"], "no_copy", 1)


_CARRY_FORWARD_CACHE_KEY = "beam:inv_dim_carry_forward"


def get_carry_forward_dims() -> list[dict]:
	"""Cached list of Inventory Dimensions with carry_forward enabled. Cleared alongside
	the scan cache when an Inventory Dimension is updated or deleted."""

	def _fetch():
		return [
			d
			for d in frappe.get_all(
				"Inventory Dimension",
				filters={"custom_carry_forward": 1},
				fields=["source_fieldname", "target_fieldname"],
			)
			if d.source_fieldname and d.target_fieldname
		]

	return frappe.cache().get_value(_CARRY_FORWARD_CACHE_KEY, generator=_fetch)


def propagate_inventory_dimensions(doc, method=None):
	"""before_submit hook for Stock Entry: copy each Inventory Dimension's source field to its
	target field on rows where target is empty. Only fires for dimensions flagged with
	`custom_carry_forward`, and only on rows that represent a real transfer (both s_warehouse
	and t_warehouse set, row has a stock item code).

	App-specific flows that explicitly set target (including explicit `None`) are unaffected
	as long as their dimension is not flagged to carry forward."""
	dims = get_carry_forward_dims()
	if not dims:
		return

	for row in doc.items or []:
		if not row.item_code or not row.s_warehouse or not row.t_warehouse:
			continue
		for dim in dims:
			if row.get(dim.source_fieldname) and not row.get(dim.target_fieldname):
				row.set(dim.target_fieldname, row.get(dim.source_fieldname))
