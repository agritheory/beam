# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

"""BEAM mobile quality inspection: gate and hold lines on source documents."""

from __future__ import annotations

import json
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, nowdate

from erpnext.controllers.stock_controller import make_quality_inspections

from beam.beam.mobile_access import ensure_document_access, mobile_quality_inspection_write

GATE_DOCTYPES = frozenset(
	{
		"Purchase Receipt",
		"Purchase Invoice",
		"Subcontracting Receipt",
		"Delivery Note",
		"Sales Invoice",
		"Stock Entry",
	}
)

HOLD_PARENT_DOCTYPES = frozenset(
	{
		"Purchase Receipt",
		"Subcontracting Receipt",
		"Stock Entry",
	}
)

CHILD_DOCTYPE = {
	"Purchase Receipt": "Purchase Receipt Item",
	"Purchase Invoice": "Purchase Invoice Item",
	"Subcontracting Receipt": "Subcontracting Receipt Item",
	"Delivery Note": "Delivery Note Item",
	"Sales Invoice": "Sales Invoice Item",
	"Stock Entry": "Stock Entry Detail",
}

INCOMING_PURPOSES = frozenset({"Manufacture", "Material Receipt"})


def child_table_field(parent_doctype: str) -> str:
	if parent_doctype == "Stock Entry":
		return "items"
	return "items"


def row_has_intended_warehouse(parent_doctype: str) -> bool:
	child = CHILD_DOCTYPE.get(parent_doctype)
	if not child:
		return False
	return bool(frappe.get_meta(child).has_field("intended_warehouse"))


def row_has_qi_reference(parent_doctype: str) -> bool:
	child = CHILD_DOCTYPE.get(parent_doctype)
	if not child:
		return False
	meta = frappe.get_meta(child)
	return meta.has_field("reference_doctype") and meta.has_field("reference_name")


def inspection_type_for_reference(reference_type: str, doc: frappe.Document | None = None) -> str:
	if reference_type in ("Purchase Receipt", "Purchase Invoice", "Subcontracting Receipt"):
		return "Incoming"
	if reference_type in ("Delivery Note", "Sales Invoice"):
		return "Outgoing"
	if reference_type == "Job Card":
		return "In Process"
	if reference_type == "Stock Entry" and doc:
		purpose = doc.get("purpose") or doc.get("stock_entry_type") or ""
		if purpose in INCOMING_PURPOSES:
			return "Incoming"
		return "Outgoing"
	return "Incoming"


def call_check_item_quality_inspection(
	doctype: str, docstatus: int, items: list[dict]
) -> list[dict]:
	method = frappe.override_whitelisted_method(
		"erpnext.controllers.stock_controller.check_item_quality_inspection"
	)
	return frappe.call(method, doctype=doctype, docstatus=docstatus, items=items)


def filter_gate_lines(doctype: str, doc: frappe.Document, candidates: list[dict]) -> list[dict]:
	"""Match ERPNext transaction.js has_inspection_required (submit gate — hide linked QI rows)."""
	filtered = []
	for item in candidates:
		if item.get("quality_inspection"):
			continue
		if (
			doctype == "Stock Entry"
			and (doc.get("purpose") or doc.get("stock_entry_type")) == "Manufacture"
		):
			if not item.get("is_finished_item"):
				continue
		filtered.append(item)
	return filtered


def incoming_inspection_item_codes(item_codes: list[str]) -> set[str]:
	if not item_codes:
		return set()
	return set(
		frappe.get_all(
			"Item",
			filters={"name": ["in", item_codes], "inspection_required_before_purchase": 1},
			pluck="name",
		)
	)


def gate_candidates_for_doc(doctype: str, docstatus: int, items_payload: list[dict]) -> list[dict]:
	checked = call_check_item_quality_inspection(doctype, docstatus, items_payload)
	if checked or doctype not in ("Purchase Receipt", "Purchase Invoice", "Subcontracting Receipt"):
		return checked
	codes = incoming_inspection_item_codes([row.get("item_code") for row in items_payload])
	return [row for row in items_payload if row.get("item_code") in codes]


def gate_rows_for_mobile_display(
	doctype: str, doc: frappe.Document, candidates: list[dict]
) -> list[frappe._dict]:
	"""All inspection-required lines with icon state, including draft/submitted QI."""
	required_names = {item.get("name") for item in candidates if item.get("name")}
	required_codes = {item.get("item_code") for item in candidates if item.get("item_code")}
	rows: list[frappe._dict] = []
	for row in doc.get("items") or []:
		if row.get("is_scrap_item"):
			continue
		matches = row.name in required_names or row.item_code in required_codes
		if not matches:
			continue
		if (
			doctype == "Stock Entry"
			and (doc.get("purpose") or doc.get("stock_entry_type")) == "Manufacture"
		):
			if not row.get("is_finished_item"):
				continue
		rows.append(row)
	return rows


def gate_applies(doc: frappe.Document) -> bool:
	doctype = doc.doctype
	if doctype == "Stock Entry":
		return bool(doc.get("inspection_required"))
	if doctype in ("Sales Invoice", "Purchase Invoice") and not doc.get("update_stock"):
		return False
	return doctype in GATE_DOCTYPES


def qi_state(quality_inspection: str | None) -> tuple[str, str | None]:
	if not quality_inspection:
		return "needed", None
	if not frappe.db.exists("Quality Inspection", quality_inspection):
		return "needed", None
	row = frappe.db.get_value(
		"Quality Inspection",
		quality_inspection,
		["docstatus", "status"],
		as_dict=True,
	)
	if not row:
		return "needed", None
	docstatus = cint(row.docstatus)
	status = row.status or ""
	if docstatus == 0:
		return "draft", status
	if docstatus == 1:
		return status or "Accepted", status
	return "needed", None


def quality_inspection_released(quality_inspection: str) -> bool:
	if not quality_inspection or not row_has_qi_reference("Stock Entry"):
		return False
	StockEntry = frappe.qb.DocType("Stock Entry")
	StockEntryDetail = frappe.qb.DocType("Stock Entry Detail")
	rows = (
		frappe.qb.from_(StockEntryDetail)
		.join(StockEntry)
		.on(StockEntryDetail.parent == StockEntry.name)
		.select(StockEntryDetail.name)
		.where(
			(StockEntry.docstatus == 1)
			& (StockEntryDetail.reference_doctype == "Quality Inspection")
			& (StockEntryDetail.reference_name == quality_inspection)
		)
		.limit(1)
	).run()
	return bool(rows)


def hold_row_from_line(parent_doctype: str, parent_name: str, row: frappe._dict) -> dict | None:
	if not row.get("intended_warehouse"):
		return None
	holding_wh = row.get("warehouse") or row.get("t_warehouse")
	qi = row.get("quality_inspection")
	state, qi_status = qi_state(qi)
	if state in ("Accepted", "Rejected") and quality_inspection_released(qi):
		state = "released"
	return {
		"row": row.name,
		"item_code": row.item_code,
		"kind": "hold",
		"quality_inspection": qi,
		"state": state,
		"qi_status": qi_status,
		"holding_warehouse": holding_wh,
		"intended_warehouse": row.intended_warehouse,
		"reference_type": parent_doctype,
		"reference_name": parent_name,
	}


def gate_row_from_line(parent_doctype: str, parent_name: str, row: frappe._dict) -> dict:
	qi = row.get("quality_inspection")
	state, qi_status = qi_state(qi)
	return {
		"row": row.name,
		"idx": row.idx,
		"item_code": row.item_code,
		"kind": "gate",
		"quality_inspection": qi,
		"state": state,
		"qi_status": qi_status,
		"reference_type": parent_doctype,
		"reference_name": parent_name,
	}


@frappe.whitelist()
def list_incoming_inspection_item_codes(item_codes: str | list | None = None) -> list[str]:
	if isinstance(item_codes, str):
		item_codes = json.loads(item_codes)
	if not item_codes:
		return []
	return sorted(incoming_inspection_item_codes(list(item_codes)))


@frappe.whitelist()
def preview_line_inspections(doctype: str, items: str | list | None = None) -> list[dict]:
	"""Gate lines for a mapped receipt that is not saved yet (no document name)."""
	if isinstance(items, str):
		items = json.loads(items)
	if not items:
		return []

	pseudo = frappe._dict({"doctype": doctype})
	if not gate_applies(pseudo):
		return []

	items_payload = [row if isinstance(row, dict) else row.as_dict() for row in items]
	checked = gate_candidates_for_doc(doctype, 0, items_payload)
	results: list[dict] = []
	for item in checked:
		qi = item.get("quality_inspection")
		state, qi_status = qi_state(qi)
		row_id = item.get("name") or str(item.get("idx") or item.get("item_code"))
		results.append(
			{
				"row": row_id,
				"idx": item.get("idx"),
				"item_code": item.get("item_code"),
				"kind": "gate",
				"quality_inspection": qi,
				"state": state,
				"qi_status": qi_status,
				"reference_type": doctype,
				"reference_name": "",
			}
		)
	return results


@frappe.whitelist()
def get_work_order_line_inspections(work_order: str) -> list[dict]:
	ensure_document_access("Work Order", work_order, "read")
	entries = frappe.get_all(
		"Stock Entry",
		filters={
			"work_order": work_order,
			"docstatus": 1,
			"stock_entry_type": "Material Transfer for Manufacture",
		},
		order_by="creation desc",
		pluck="name",
		limit=1,
	)
	if not entries:
		return []
	return get_line_inspections("Stock Entry", entries[0])


@frappe.whitelist()
def get_line_inspections(doctype: str, name: str) -> list[dict]:
	ensure_document_access(doctype, name, "read")
	doc = frappe.get_doc(doctype, name)
	results: list[dict] = []

	if doc.docstatus == 1:
		if row_has_intended_warehouse(doctype):
			for row in doc.get("items") or []:
				if row.get("is_scrap_item"):
					continue
				hold = hold_row_from_line(doctype, name, row)
				if hold:
					results.append(hold)
			return results
		if gate_applies(doc):
			items_payload = [
				row.as_dict() for row in doc.get("items") or [] if not row.get("is_scrap_item")
			]
			checked = gate_candidates_for_doc(doctype, doc.docstatus, items_payload)
			for row in gate_rows_for_mobile_display(doctype, doc, checked):
				results.append(gate_row_from_line(doctype, name, row))
		return results

	if not gate_applies(doc):
		return results

	items_payload = [row.as_dict() for row in doc.get("items") or [] if not row.get("is_scrap_item")]
	checked = gate_candidates_for_doc(doctype, doc.docstatus, items_payload)
	for row in gate_rows_for_mobile_display(doctype, doc, checked):
		results.append(gate_row_from_line(doctype, name, row))
	return results


def line_needs_attention(line_info: dict) -> bool:
	state = line_info.get("state")
	if state in ("needed", "draft", "Rejected"):
		return True
	if state == "Accepted" and line_info.get("kind") == "hold":
		return not quality_inspection_released(line_info.get("quality_inspection"))
	return False


@frappe.whitelist()
def list_awaiting_inspection(filters: str | None = None, page: int = 1) -> list[dict]:
	page = max(1, cint(page))
	page_len = 20
	start = (page - 1) * page_len
	filter_dict = json.loads(filters) if filters else {}

	rows: list[dict] = []

	if row_has_intended_warehouse("Purchase Receipt"):
		rows.extend(_awaiting_hold_lines(start, page_len, filter_dict))

	rows.extend(_awaiting_gate_lines(start, page_len, filter_dict))

	rows.sort(key=lambda r: (r.get("schedule_date") or "", r.get("reference_name") or ""))
	return rows[:page_len]


def _awaiting_hold_lines(start: int, page_len: int, filters: dict) -> list[dict]:
	"""Submitted lines parked in quarantine awaiting inspection or release."""
	out: list[dict] = []
	for parent_doctype, child_doctype in (
		("Purchase Receipt", "Purchase Receipt Item"),
		("Subcontracting Receipt", "Subcontracting Receipt Item"),
		("Stock Entry", "Stock Entry Detail"),
	):
		if not row_has_intended_warehouse(parent_doctype):
			continue
		parent = frappe.qb.DocType(parent_doctype)
		child = frappe.qb.DocType(child_doctype)
		query = (
			frappe.qb.from_(child)
			.join(parent)
			.on(child.parent == parent.name)
			.select(
				child.name.as_("row"),
				child.item_code,
				child.parent.as_("reference_name"),
				parent.modified,
				child.qty,
				child.intended_warehouse,
				child.warehouse,
				child.t_warehouse,
				child.quality_inspection,
			)
			.where(
				(parent.docstatus == 1)
				& (child.intended_warehouse.isnotnull())
				& (child.intended_warehouse != "")
			)
			.orderby(parent.modified, order=frappe.qb.desc)
			.limit(page_len)
			.offset(start)
		)
		for record in query.run(as_dict=True):
			holding = record.t_warehouse or record.warehouse
			qi = record.quality_inspection
			state, _ = qi_state(qi)
			if state in ("Accepted", "Rejected") and quality_inspection_released(qi):
				continue
			if state not in ("needed", "draft", "Rejected", "Accepted"):
				continue
			if state == "Accepted" and quality_inspection_released(qi):
				continue
			out.append(
				{
					"row": record.row,
					"item_code": record.item_code,
					"reference_type": parent_doctype,
					"reference_name": record.reference_name,
					"kind": "hold",
					"qty": flt(record.qty),
					"holding_warehouse": holding,
					"intended_warehouse": record.intended_warehouse,
					"quality_inspection": qi,
					"state": state,
					"schedule_date": str(getdate(record.modified)),
				}
			)
	return out


def _awaiting_gate_lines(start: int, page_len: int, filters: dict) -> list[dict]:
	out: list[dict] = []
	for doctype in ("Purchase Receipt", "Delivery Note", "Stock Entry"):
		names = frappe.get_all(
			doctype,
			filters={"docstatus": 0},
			pluck="name",
			order_by="modified desc",
			limit_start=start,
			limit_page_length=page_len,
		)
		for name in names:
			for line in get_line_inspections(doctype, name):
				if line_needs_attention(line):
					doc = frappe.get_cached_doc(doctype, name)
					row = next(r for r in doc.items if r.name == line["row"])
					out.append(
						{
							**line,
							"qty": flt(row.qty),
							"schedule_date": str(getdate(doc.get("posting_date") or doc.modified)),
						}
					)
	return out


def correction_mode(
	reference_type: str, reference_name: str, row_name: str, qi_name: str | None
) -> str | None:
	if not qi_name:
		return None
	doc = frappe.get_cached_doc(reference_type, reference_name)
	qi_docstatus = frappe.db.get_value("Quality Inspection", qi_name, "docstatus")
	if doc.docstatus == 0 and qi_docstatus == 1:
		return "amend"
	if doc.docstatus == 1 and qi_name:
		_, status = qi_state(qi_name)
		if status == "Rejected":
			row = next((r for r in doc.items if r.name == row_name), None)
			if row and row.get("intended_warehouse") and not quality_inspection_released(qi_name):
				return "reinspect"
	return None


def reading_hint(reading: frappe._dict) -> str:
	if reading.get("formula_based_criteria"):
		return _("Checked on submit")
	if cint(reading.get("numeric")):
		min_v = reading.get("min_value")
		max_v = reading.get("max_value")
		if min_v is not None or max_v is not None:
			return f"{min_v} – {max_v}"
		return ""
	if reading.get("value"):
		return _("expected: {0}").format(reading.value)
	return ""


def reading_entry_kind(reading: frappe._dict) -> str:
	return mobile_reading_kind_from_qi_row(reading)


def template_reading_kind(param: dict) -> str:
	"""Map template row to mobile reading UI (ERPNext params have no manual_inspection field)."""
	if cint(param.get("manual_inspection")):
		return "passfail"
	if param.get("formula_based_criteria"):
		return "numeric"
	if cint(param.get("numeric", 1)):
		return "numeric"
	if param.get("value"):
		return "text"
	return "passfail"


def mobile_reading_kind_from_qi_row(reading: frappe._dict) -> str:
	return template_reading_kind(
		{
			"formula_based_criteria": reading.formula_based_criteria,
			"numeric": reading.numeric,
			"value": reading.value,
			"manual_inspection": reading.manual_inspection,
		}
	)


def parse_inspection_answers(answers: str | dict | None) -> dict[str, list[str]]:
	if answers is None:
		return {}
	if isinstance(answers, str):
		answers = json.loads(answers)
	if isinstance(answers, str):
		answers = json.loads(answers)
	if not isinstance(answers, dict):
		frappe.throw(_("Invalid inspection answers"))
	out: dict[str, list[str]] = {}
	for key, values in answers.items():
		if isinstance(values, list):
			out[str(key)] = [str(v) for v in values]
		elif values is None:
			out[str(key)] = []
		else:
			out[str(key)] = [str(values)]
	return out


def quality_inspection_name_for_line(
	reference_type: str,
	reference_name: str,
	row_name: str,
	preferred: str | None = None,
	*,
	draft_only: bool = False,
) -> str | None:
	if preferred and frappe.db.exists("Quality Inspection", preferred):
		preferred_status = frappe.db.get_value("Quality Inspection", preferred, "docstatus")
		if not draft_only or cint(preferred_status) == 0:
			return preferred

	filters: dict[str, Any] = {
		"reference_type": reference_type,
		"reference_name": reference_name,
		"child_row_reference": row_name,
	}
	if draft_only:
		filters["docstatus"] = 0
	else:
		filters["docstatus"] = ("<", 2)

	rows = frappe.get_all(
		"Quality Inspection",
		filters=filters,
		pluck="name",
		order_by="modified desc",
		limit=1,
	)
	return rows[0] if rows else None


def link_quality_inspection_to_row(
	reference_type: str, row_name: str, quality_inspection: str
) -> None:
	child_doctype = CHILD_DOCTYPE.get(reference_type)
	if not child_doctype:
		return
	frappe.db.set_value(
		child_doctype,
		row_name,
		"quality_inspection",
		quality_inspection,
		update_modified=False,
	)


def serialize_readings(qi: frappe.Document) -> list[dict]:
	out = []
	for reading in qi.readings:
		kind = mobile_reading_kind_from_qi_row(reading)
		entry: dict[str, Any] = {
			"parameter": reading.specification,
			"label": reading.specification,
			"kind": kind,
			"hint": reading_hint(reading),
			"values": [],
		}
		if kind == "numeric":
			for i in range(1, 11):
				val = reading.get(f"reading_{i}")
				if val is not None and str(val).strip():
					entry["values"].append(str(val))
		elif kind == "text":
			entry["values"] = [reading.reading_value or ""]
		else:
			entry["values"] = [reading.status or ""]
		out.append(entry)
	return out


@frappe.whitelist()
def open_inspection(doctype: str, name: str, row: str) -> dict:
	ensure_document_access(doctype, name, "read")
	doc = frappe.get_doc(doctype, name)
	line = next((r for r in doc.items if r.name == row), None)
	if not line:
		frappe.throw(_("Line not found"))

	lines = get_line_inspections(doctype, name)
	info = next((entry for entry in lines if entry["row"] == row), None)
	if not info:
		frappe.throw(_("This line does not require inspection"))

	qi_name = quality_inspection_name_for_line(doctype, name, row, line.quality_inspection)
	editable = True
	readings: list[dict] = []
	sample_size = 1

	if qi_name and frappe.db.exists("Quality Inspection", qi_name):
		qi = frappe.get_doc("Quality Inspection", qi_name)
		if qi.docstatus == 1:
			editable = False
		readings = serialize_readings(qi)
		sample_size = cint(qi.sample_size) or 1
	else:
		template = frappe.db.get_value("Item", line.item_code, "quality_inspection_template")
		if not template:
			frappe.throw(_("No Quality Inspection Template on item {0}").format(line.item_code))
		from erpnext.stock.doctype.quality_inspection_template.quality_inspection_template import (
			get_template_details,
		)

		for param in get_template_details(template):
			kind = template_reading_kind(param)
			readings.append(
				{
					"parameter": param["specification"],
					"label": param["specification"],
					"kind": kind,
					"hint": reading_hint(frappe._dict(param)),
					"values": [],
				}
			)

	mode = correction_mode(doctype, name, row, qi_name)
	if qi_name and frappe.db.get_value("Quality Inspection", qi_name, "docstatus") == 1 and not mode:
		editable = False

	can_release = (
		info.get("kind") == "hold"
		and info.get("state") == "Accepted"
		and qi_name
		and not quality_inspection_released(qi_name)
	)

	return {
		"reference_type": doctype,
		"reference_name": name,
		"purchase_order": line.get("purchase_order") if doctype == "Purchase Receipt" else None,
		"row": row,
		"item_code": line.item_code,
		"item_name": line.item_name,
		"batch_no": line.get("batch_no"),
		"serial_no": (line.get("serial_no") or "").split("\n")[0] if line.get("serial_no") else None,
		"sample_size": sample_size,
		"readings": readings,
		"editable": editable,
		"correction": mode,
		"kind": info.get("kind"),
		"quality_inspection": qi_name,
		"status": info.get("qi_status") or info.get("state"),
		"can_release": can_release,
	}


def answer_values_are_empty(values: list[str], kind: str) -> bool:
	if kind == "passfail":
		return not values or values[0] not in ("Accepted", "Rejected")
	if kind == "text":
		return not values or not str(values[0]).strip()
	return not any(str(v).strip() for v in values)


def save_qi_draft(qi: frappe.Document) -> None:
	"""Persist draft readings without ERPNext validate (inspect_and_set_status on all rows)."""
	qi.flags.ignore_validate = True
	try:
		qi.save()
	finally:
		qi.flags.ignore_validate = False


def normalize_qi_numeric_readings(qi: frappe.Document) -> None:
	"""ERPNext QI validate expects reading_1..10 as strings (calls .strip())."""
	for reading in qi.readings:
		if reading_entry_kind(reading) != "numeric":
			continue
		for i in range(1, 11):
			field = f"reading_{i}"
			val = reading.get(field)
			if val is None or isinstance(val, str):
				continue
			reading.set(field, str(val).strip())


def apply_answers_to_qi(
	qi: frappe.Document,
	sample_size: int,
	answers: dict[str, list[str]],
	*,
	merge: bool = True,
) -> None:
	qi.sample_size = flt(sample_size)
	for reading in qi.readings:
		spec = reading.specification
		if spec not in answers:
			continue
		values = answers[spec]
		kind = reading_entry_kind(reading)
		if merge and answer_values_are_empty(values, kind):
			continue
		if kind == "numeric":
			for i in range(1, 11):
				reading.set(f"reading_{i}", None)
			for idx, val in enumerate(values[:10], start=1):
				text = str(val).strip() if val is not None else ""
				# ERPNext validate uses .strip() on reading_N; store strings not floats.
				reading.set(f"reading_{idx}", text if text else None)
		elif kind == "text":
			reading.reading_value = values[0] if values else ""
		else:
			status = values[0] if values else ""
			if status in ("Accepted", "Rejected"):
				reading.status = status


def upsert_quality_inspection_for_line(
	doctype: str,
	name: str,
	row: str,
	sample_size: int,
	answers: dict,
	*,
	submit: bool,
) -> dict:
	ensure_document_access(doctype, name, "write")

	with mobile_quality_inspection_write():
		doc = frappe.get_doc(doctype, name)
		line = next((r for r in doc.items if r.name == row), None)
		if not line:
			frappe.throw(_("Line not found"))

		form = open_inspection(doctype, name, row)
		if not form.get("editable"):
			frappe.throw(_("This inspection cannot be edited on mobile"))

		qi_name = quality_inspection_name_for_line(
			doctype, name, line.name, line.quality_inspection, draft_only=True
		)
		if qi_name and frappe.db.get_value("Quality Inspection", qi_name, "docstatus") == 1:
			frappe.throw(_("Quality Inspection is already submitted"))

		if qi_name and frappe.db.exists("Quality Inspection", qi_name):
			qi = frappe.get_doc("Quality Inspection", qi_name)
		else:
			created = make_quality_inspections(
				doc.company,
				doctype,
				name,
				[
					{
						"item_code": line.item_code,
						"item_name": line.item_name,
						"description": line.description,
						"qty": line.qty,
						"sample_size": flt(sample_size),
						"serial_no": line.get("serial_no"),
						"batch_no": line.get("batch_no"),
						"child_row_reference": line.name,
					}
				],
			)
			if not created:
				frappe.throw(_("Could not create Quality Inspection"))
			qi = frappe.get_doc("Quality Inspection", created[0])
			qi.inspection_type = inspection_type_for_reference(doctype, doc)
			qi.get_item_specification_details()
			save_qi_draft(qi)

		merge_answers = not submit
		apply_answers_to_qi(qi, sample_size, answers, merge=merge_answers)
		if submit:
			normalize_qi_numeric_readings(qi)
			qi.save()
			link_quality_inspection_to_row(doctype, line.name, qi.name)
			qi.update_qc_reference()
			qi.submit()
		else:
			save_qi_draft(qi)
			link_quality_inspection_to_row(doctype, line.name, qi.name)
			qi.update_qc_reference()

		can_release = (
			form.get("kind") == "hold"
			and qi.status == "Accepted"
			and not quality_inspection_released(qi.name)
		)

		return {
			"name": qi.name,
			"status": qi.status,
			"can_release": can_release,
			"readings": serialize_readings(qi),
			"quality_inspection": qi.name,
		}


@frappe.whitelist()
def discard_inspection_draft(doctype: str, name: str, row: str) -> dict:
	ensure_document_access(doctype, name, "write")

	with mobile_quality_inspection_write():
		doc = frappe.get_doc(doctype, name)
		line = next((r for r in doc.items if r.name == row), None)
		if not line:
			frappe.throw(_("Line not found"))

		qi_name = quality_inspection_name_for_line(
			doctype, name, line.name, line.quality_inspection, draft_only=True
		)
		if not qi_name:
			return open_inspection(doctype, name, row)

		if cint(frappe.db.get_value("Quality Inspection", qi_name, "docstatus")) != 0:
			frappe.throw(_("Only draft inspections can be discarded"))

		qi = frappe.get_doc("Quality Inspection", qi_name)
		link_quality_inspection_to_row(doctype, line.name, "")
		qi.update_qc_reference(remove_reference=True)
		frappe.delete_doc("Quality Inspection", qi_name, force=True)

	return open_inspection(doctype, name, row)


@frappe.whitelist()
def save_inspection_draft(
	doctype: str,
	name: str,
	row: str,
	sample_size: int = 1,
	answers: str | dict | None = None,
) -> dict:
	answers = parse_inspection_answers(answers)
	return upsert_quality_inspection_for_line(doctype, name, row, sample_size, answers, submit=False)


@frappe.whitelist()
def submit_inspection(
	doctype: str,
	name: str,
	row: str,
	sample_size: int = 1,
	answers: str | dict | None = None,
) -> dict:
	answers = parse_inspection_answers(answers)
	return upsert_quality_inspection_for_line(doctype, name, row, sample_size, answers, submit=True)


@frappe.whitelist()
def reinspect(quality_inspection: str) -> dict:
	qi = frappe.get_doc("Quality Inspection", quality_inspection)
	mode = correction_mode(qi.reference_type, qi.reference_name, qi.child_row_reference, qi.name)
	if mode == "amend":
		if qi.docstatus != 1:
			frappe.throw(_("Only submitted inspections can be amended"))
		amended = frappe.copy_doc(qi)
		amended.docstatus = 0
		amended.amended_from = qi.name
		qi.cancel()
		amended.insert()
		return open_inspection(qi.reference_type, qi.reference_name, qi.child_row_reference)

	if mode == "reinspect":
		doc = frappe.get_doc(qi.reference_type, qi.reference_name)
		line = next((r for r in doc.items if r.name == qi.child_row_reference), None)
		if not line:
			frappe.throw(_("Source line not found"))
		line.db_set("quality_inspection", None)
		return open_inspection(qi.reference_type, qi.reference_name, qi.child_row_reference)

	frappe.throw(_("This inspection cannot be corrected on mobile"))


@frappe.whitelist()
def release_from_quarantine(quality_inspection: str) -> str:
	method = (
		"inventory_tools.inventory_tools.overrides.stock_entry.make_quarantine_release_stock_entry"
	)
	if not frappe.get_hooks(app_name="inventory_tools"):
		frappe.throw(_("Inventory Tools is not installed"))
	return frappe.call(method, quality_inspection_name=quality_inspection)
