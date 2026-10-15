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
	template.append(
		"item_quality_inspection_parameter",
		{
			"specification": "Visual",
			"numeric": 0,
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


def find_beam_qi_purchase_order() -> str | None:
	for po_name in frappe.get_all(
		"Purchase Order",
		filters={"supplier": BEAM_QI_SUPPLIER, "docstatus": 1},
		pluck="name",
		order_by="creation desc",
	):
		if frappe.db.count("Purchase Order Item", {"parent": po_name, "item_code": BEAM_QI_ITEM}) >= 1:
			return po_name
	return None


def ensure_beam_qi_purchase_order(settings) -> str:
	configure_beam_qi_item()
	existing = find_beam_qi_purchase_order()
	if existing:
		return existing

	po = frappe.new_doc("Purchase Order")
	po.supplier = BEAM_QI_SUPPLIER
	po.company = settings.company
	po.schedule_date = frappe.utils.today()
	po.append(
		"items",
		{
			"item_code": BEAM_QI_ITEM,
			"qty": 2,
			"rate": 1,
			"warehouse": BEAM_QI_WAREHOUSE,
		},
	)
	po.insert()
	po.submit()
	return po.name


def ensure_beam_qi_draft_receipt(settings) -> str:
	po_name = ensure_beam_qi_purchase_order(settings)
	for pr in frappe.get_all("Purchase Receipt", filters={"docstatus": 0}, pluck="name"):
		if frappe.db.exists("Purchase Receipt Item", {"parent": pr, "item_code": BEAM_QI_ITEM}):
			return pr

	pr = make_purchase_receipt(po_name)
	pr.insert()
	return pr.name


def setup_beam_quality_inspection_fixtures(settings) -> None:
	remove_legacy_qi_demo_item()
	configure_beam_qi_item()
	ensure_beam_qi_draft_receipt(settings)
	frappe.db.commit()
