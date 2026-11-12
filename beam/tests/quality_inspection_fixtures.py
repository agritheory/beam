# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt

BEAM_QI_TEMPLATE = "BEAM Mobile QI Template"
BEAM_QI_ITEM = "Flour"
BEAM_QI_SUPPLIER = "Freedom Provisions"
BEAM_QI_WAREHOUSE = "Receiving - APC"

LEGACY_QI_DEMO_ITEM = "Beam QI Demo Item"


def ensure_quality_inspection_parameter(parameter: str) -> None:
	if frappe.db.exists("Quality Inspection Parameter", parameter):
		return
	frappe.get_doc(
		{
			"doctype": "Quality Inspection Parameter",
			"parameter": parameter,
			"description": parameter,
		}
	).insert()


def ensure_beam_qi_template() -> str:
	if frappe.db.exists("Quality Inspection Template", BEAM_QI_TEMPLATE):
		return BEAM_QI_TEMPLATE

	for name in ("Diameter", "Weight", "Color"):
		ensure_quality_inspection_parameter(name)
	ensure_quality_inspection_parameter("Visual")

	template = frappe.new_doc("Quality Inspection Template")
	template.quality_inspection_template_name = BEAM_QI_TEMPLATE
	template.append(
		"item_quality_inspection_parameter",
		{
			"specification": "Diameter",
			"numeric": 1,
			"min_value": 10,
			"max_value": 12,
		},
	)
	template.append(
		"item_quality_inspection_parameter",
		{
			"specification": "Weight",
			"numeric": 1,
			"formula_based_criteria": 1,
			"acceptance_formula": "mean > 4.5",
		},
	)
	template.append(
		"item_quality_inspection_parameter",
		{
			"specification": "Color",
			"numeric": 0,
			"value": "Natural",
		},
	)
	template.insert()
	return template.name


def configure_beam_qi_item(item_code: str = BEAM_QI_ITEM) -> None:
	ensure_beam_qi_template()
	item = frappe.get_doc("Item", item_code)
	item.inspection_required_before_purchase = 1
	item.quality_inspection_template = BEAM_QI_TEMPLATE
	item.save()


def remove_legacy_qi_demo_item() -> None:
	if not frappe.db.exists("Item", LEGACY_QI_DEMO_ITEM):
		return
	frappe.delete_doc("Item", LEGACY_QI_DEMO_ITEM, force=True)


def create_beam_qi_purchase_order(settings, qty: float = 10) -> str:
	"""New submitted PO with open Flour qty (never reuse production-plan POs)."""
	configure_beam_qi_item()
	po = frappe.new_doc("Purchase Order")
	po.supplier = BEAM_QI_SUPPLIER
	po.company = settings.company
	po.schedule_date = frappe.utils.today()
	po.append(
		"items",
		{
			"item_code": BEAM_QI_ITEM,
			"qty": qty,
			"rate": 1,
			"warehouse": BEAM_QI_WAREHOUSE,
		},
	)
	po.insert()
	po.submit()
	return po.name


def purchase_order_for_receipt(pr_name: str) -> str:
	po = frappe.db.get_value("Purchase Receipt Item", {"parent": pr_name}, "purchase_order")
	if not po:
		frappe.throw(f"No purchase order on Purchase Receipt {pr_name}")
	return po


def ensure_beam_qi_draft_receipt(settings) -> str:
	"""Fresh draft PR for QI tests (avoid reusing rows with submitted inspections)."""
	po_name = create_beam_qi_purchase_order(settings)
	pr = make_purchase_receipt(po_name)
	pr.insert()
	return pr.name


def ensure_beam_qi_draft_receipt_committed(settings) -> str:
	"""Draft receipt visible to bench serve (Playwright)."""
	pr_name = ensure_beam_qi_draft_receipt(settings)
	frappe.db.commit()
	return pr_name


def setup_beam_quality_inspection_fixtures(settings) -> None:
	"""Global setup: template + legacy cleanup only (Flour gate is enabled in QI tests)."""
	remove_legacy_qi_demo_item()
	frappe.db.commit()


def enable_flour_incoming_inspection() -> None:
	configure_beam_qi_item(BEAM_QI_ITEM)


def disable_flour_incoming_inspection() -> None:
	if not frappe.db.exists("Item", BEAM_QI_ITEM):
		return
	frappe.db.set_value(
		"Item",
		BEAM_QI_ITEM,
		{"inspection_required_before_purchase": 0, "quality_inspection_template": None},
	)
