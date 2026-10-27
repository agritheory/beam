# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry


def associate_handling_units_on_stock_entry(se_dict: dict) -> None:
	for row in se_dict.get("items") or []:
		item_code = row.get("item_code")
		if not item_code or not frappe.get_value("Item", item_code, "is_stock_item"):
			continue
		if not frappe.get_value("Item", item_code, "enable_handling_unit"):
			continue
		hu = frappe.db.get_value("Purchase Receipt Item", {"item_code": item_code}, "handling_unit")
		if not hu:
			hu = frappe.db.get_value("Purchase Invoice Item", {"item_code": item_code}, "handling_unit")
		if not hu:
			hu = frappe.db.get_value(
				"Stock Ledger Entry",
				{
					"item_code": item_code,
					"warehouse": row.get("s_warehouse"),
					"handling_unit": ("is", "set"),
				},
				"handling_unit",
				order_by="creation desc",
			)
		if not hu:
			continue
		scan = frappe.call(
			"beam.beam.scan.scan",
			**{
				"barcode": str(hu),
				"context": {"frm": "Stock Entry", "doc": se_dict},
				"current_qty": 1,
			},
		)
		row["handling_unit"] = scan[0]["context"].get("handling_unit")


def submit_material_transfer_for_manufacture(work_order: str, qty: float) -> str:
	se_dict = make_stock_entry(work_order, "Material Transfer for Manufacture", qty)
	associate_handling_units_on_stock_entry(se_dict)
	se = frappe.get_doc(**se_dict)
	disabled_hu_items: list[str] = []
	try:
		for row in se.items:
			if not frappe.get_value("Item", row.item_code, "enable_handling_unit"):
				continue
			if row.handling_unit:
				continue
			frappe.db.set_value("Item", row.item_code, "enable_handling_unit", 0)
			disabled_hu_items.append(row.item_code)
		if disabled_hu_items:
			frappe.db.commit()
		se.save()
		se.submit()
	finally:
		for item_code in disabled_hu_items:
			frappe.db.set_value("Item", item_code, "enable_handling_unit", 1)
		if disabled_hu_items:
			frappe.db.commit()
	return se.name


def pause_open_job_cards_for_user(user_email: str) -> None:
	employee = frappe.db.get_value("Employee", {"user_id": user_email, "status": "Active"}, "name")
	if not employee:
		return
	open_cards = frappe.db.sql(
		"""
		select distinct parent
		from `tabJob Card Time Log`
		where employee = %s and ifnull(to_time, '') = ''
		""",
		employee,
	)
	for (job_card_id,) in open_cards:
		try:
			frappe.call(
				"beam.beam.manufacturing.pause_job_card",
				job_card_id=job_card_id,
				completed_qty=0,
			)
		except Exception:
			continue
