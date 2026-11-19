# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry
from frappe.utils import flt

from beam.beam.scan import get_handling_unit


def handling_unit_has_stock(hu: str, item_code: str, warehouse: str | None = None) -> bool:
	details = get_handling_unit(hu)
	if not details or details.item_code != item_code:
		return False
	if warehouse and details.warehouse != warehouse:
		return False
	return flt(details.stock_qty) > 0


def handling_unit_with_stock(item_code: str, warehouse: str | None = None) -> str | None:
	"""Handling unit from a submitted receipt/invoice that still has on-hand stock."""
	candidates: list[str] = []
	for parent_doctype in ("Purchase Invoice", "Purchase Receipt"):
		child_doctype = f"{parent_doctype} Item"
		for parent in frappe.get_all(
			parent_doctype,
			filters={"docstatus": 1},
			pluck="name",
			order_by="posting_date desc, creation desc",
		):
			filters = {
				"parent": parent,
				"item_code": item_code,
				"handling_unit": ("is", "set"),
			}
			if warehouse:
				filters["warehouse"] = warehouse
			hu = frappe.db.get_value(child_doctype, filters, "handling_unit")
			if hu:
				candidates.append(hu)

	sle_filters = {"item_code": item_code, "handling_unit": ("is", "set"), "is_cancelled": 0}
	if warehouse:
		sle_filters["warehouse"] = warehouse
	for hu in frappe.get_all(
		"Stock Ledger Entry",
		filters=sle_filters,
		pluck="handling_unit",
		order_by="posting_date desc, creation desc",
	):
		if hu:
			candidates.append(hu)

	seen: set[str] = set()
	for hu in candidates:
		if hu in seen:
			continue
		seen.add(hu)
		if handling_unit_has_stock(hu, item_code, warehouse):
			return hu
	return None


def associate_handling_units_on_stock_entry(se_dict: dict) -> None:
	for row in se_dict.get("items") or []:
		item_code = row.get("item_code")
		if not item_code or not frappe.get_value("Item", item_code, "is_stock_item"):
			continue
		if not frappe.get_value("Item", item_code, "enable_handling_unit"):
			continue
		hu = handling_unit_with_stock(item_code, row.get("s_warehouse"))
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


def replenish_item_for_handling_unit_transfer(
	item_code: str, warehouse: str, qty: float, company: str | None = None
) -> None:
	if qty <= 0:
		return
	hu = handling_unit_with_stock(item_code, warehouse)
	if hu:
		details = get_handling_unit(hu)
		if details and flt(details.stock_qty) >= qty:
			return
	company = company or frappe.defaults.get_defaults().get("company")
	rate = (
		frappe.get_value("Item Price", {"item_code": item_code, "buying": 1}, "price_list_rate") or 1
	)
	se = frappe.new_doc("Stock Entry")
	se.company = company
	se.stock_entry_type = se.purpose = "Material Receipt"
	se.append(
		"items",
		{
			"item_code": item_code,
			"qty": qty,
			"t_warehouse": warehouse,
			"basic_rate": rate,
		},
	)
	se.insert()
	se.submit()


def replenish_work_order_handling_unit_stock(work_order: str) -> None:
	wo = frappe.get_doc("Work Order", work_order)
	for req in wo.required_items:
		if not frappe.get_value("Item", req.item_code, "enable_handling_unit"):
			continue
		warehouse = req.source_warehouse or req.warehouse
		if not warehouse:
			continue
		needed = flt(req.required_qty) * 2
		replenish_item_for_handling_unit_transfer(req.item_code, warehouse, needed, wo.company)


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
