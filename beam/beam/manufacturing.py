# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import json
from contextlib import contextmanager

import frappe
from erpnext.manufacturing.doctype.work_order.work_order import stop_unstop
from frappe.utils import flt, now_datetime

from beam.beam.pick_list import get_open_pick_list_for_work_order


def check_manufacturing_permission() -> None:
	allowed_roles = {"Manufacturing User", "Manufacturing Manager", "System Manager"}
	if not allowed_roles.intersection(frappe.get_roles()):
		frappe.throw(frappe._("Not permitted"), frappe.PermissionError)


def get_current_employee() -> str | None:
	employees = frappe.get_all(
		"Employee",
		filters=[["user_id", "=", frappe.session.user], ["status", "=", "Active"]],
		pluck="name",
		limit=1,
	)
	return employees[0] if employees else None


@contextmanager
def ignoring_user_permissions():
	frappe.flags.ignore_user_permissions = True
	try:
		yield
	finally:
		frappe.flags.ignore_user_permissions = False


def fetch_job_card(job_card_id: str):
	with ignoring_user_permissions():
		return frappe.get_doc("Job Card", job_card_id)


def overproduction_percentage() -> float:
	return flt(
		frappe.db.get_single_value("Manufacturing Settings", "overproduction_percentage_for_work_order")
	)


def production_qty_limits(for_quantity: float) -> tuple[float, float]:
	"""Return the minimum and maximum completed qty for a job card.

	Manufacturing Settings has one allowance, Overproduction Percentage For Work Order.
	The same percentage is the under floor and the over ceiling around Qty to Manufacture.
	"""
	target = flt(for_quantity)
	allowance = target * overproduction_percentage() / 100
	return target - allowance, target + allowance


def projected_completed_qty(doc, session_qty: float) -> float:
	"""Completed qty after writing session_qty onto the open time log."""
	open_qty = sum(flt(log.completed_qty) for log in doc.time_logs if not log.to_time)
	return flt(doc.total_completed_qty) - flt(open_qty) + flt(session_qty)


def materials_in_wip(doc) -> bool:
	"""Whether time can start, matching the Job Card timer's WIP rule.

	ERPNext only enforces that rule when the job card carries its own raw materials.
	Beam transfers against the Work Order, so the job card has no items and the timer
	check never runs. Require the work order itself to have material in WIP first.
	"""
	if doc.is_corrective_job_card or not doc.work_order:
		return True

	skip_transfer, status, transferred = frappe.db.get_value(
		"Work Order",
		doc.work_order,
		["skip_transfer", "status", "material_transferred_for_manufacturing"],
	)
	if skip_transfer:
		return True

	if doc.items:
		pending = any(flt(row.transferred_qty) < flt(row.required_qty) for row in doc.items)
		if pending:
			return False
		return status == "In Process" or flt(doc.transferred_qty) > 0

	if status == "In Process" or flt(transferred) > 0:
		return True

	work_order = frappe.get_doc("Work Order", doc.work_order)
	return bool(work_order.has_transferred_material())


def get_work_order_predecessors(work_order_id: str) -> list[dict]:
	work_order = frappe.get_doc("Work Order", work_order_id)
	if not work_order.production_plan:
		return []

	predecessors: list[dict] = []
	for row in work_order.required_items:
		if not row.item_code:
			continue

		candidates = frappe.get_all(
			"Work Order",
			filters={
				"production_plan": work_order.production_plan,
				"production_item": row.item_code,
				"name": ["!=", work_order.name],
				"status": ["not in", ["Cancelled", "Closed"]],
			},
			fields=["name", "production_item", "status", "produced_qty", "qty"],
		)
		for candidate in candidates:
			predecessors.append(
				{
					"work_order": candidate.name,
					"item_code": row.item_code,
					"required_qty": flt(row.required_qty),
					"produced_qty": flt(candidate.produced_qty),
					"status": candidate.status,
					"stock_uom": row.stock_uom,
				}
			)

	return predecessors


def predecessors_block(predecessors: list[dict]) -> bool:
	return any(flt(row["produced_qty"]) < flt(row["required_qty"]) for row in predecessors)


def require_predecessors_met(work_order_id: str) -> None:
	if predecessors_block(get_work_order_predecessors(work_order_id)):
		frappe.throw(
			frappe._("Complete predecessor work orders before continuing."),
			frappe.ValidationError,
		)


def require_materials_in_wip(doc) -> None:
	if materials_in_wip(doc):
		return

	frappe.throw(
		frappe._(
			"Materials needs to be transferred to the work in progress warehouse for the job card {0}"
		).format(doc.name)
	)


def get_locked_by_employee(doc) -> str | None:
	"""Return the employee name holding an open time log, if it belongs to someone else."""
	current_employee = get_current_employee()
	for log in doc.time_logs:
		if not log.to_time and log.employee and log.employee != current_employee:
			return log.employee
	return None


def make_time_log(args: frappe._dict) -> None:
	"""
	Replicate ERPNext's make_time_log but with ignore_permissions on the doc so that
	User Permissions on the employee link field don't block the save.
	Business-logic validations (sequence, overlap, qty) are still executed by ERPNext.
	"""
	with ignoring_user_permissions():
		doc = frappe.get_doc("Job Card", args.job_card_id)
		doc.flags.ignore_permissions = True
		doc.validate_sequence_id()
		ensure_employee_on_job_card(doc, args)
		doc.add_time_log(args)


def ensure_employee_on_job_card(doc, args: frappe._dict) -> None:
	"""
	ERPNext only populates the Job Card employee field when it is empty (first start).
	When a second employee picks up paused work, we add them here so the field always
	reflects every participant.
	"""
	employees = args.get("employees") or []
	if isinstance(employees, str):
		employees = json.loads(employees)

	existing = {row.employee for row in doc.employee if row.employee}
	for entry in employees:
		emp = entry.get("employee")
		if emp and emp not in existing:
			doc.append("employee", {"employee": emp, "completed_qty": 0.0})
			existing.add(emp)


@frappe.whitelist()
def get_work_order_mobile_context(work_order_id: str) -> dict:
	check_manufacturing_permission()
	predecessors = get_work_order_predecessors(work_order_id)
	return {
		"predecessors": predecessors,
		"predecessors_block": predecessors_block(predecessors),
		"overproduction_percentage": overproduction_percentage(),
		"pick_list": get_open_pick_list_for_work_order(work_order_id),
	}


@frappe.whitelist()
def set_work_order_status(work_order_id: str, status: str) -> str:
	check_manufacturing_permission()
	if status not in ("Stopped", "Resumed"):
		frappe.throw(frappe._("Unsupported work order status change."), frappe.ValidationError)

	return stop_unstop(work_order_id, status)


@frappe.whitelist()
def get_job_card(job_card_id: str) -> dict:
	"""
	Fetch a Job Card bypassing User Permissions on the employee link field.

	Manufacturing Users have role-level read access to all Job Cards, but Frappe's
	User Permission system restricts access when the time log references an employee
	that belongs to a different user. This endpoint enforces role-level permission
	while bypassing the employee-link User Permission check so any Manufacturing User
	can view (and continue) a job card started by a colleague.
	"""
	check_manufacturing_permission()
	doc = fetch_job_card(job_card_id)
	result = doc.as_dict()
	result["locked_by_employee"] = get_locked_by_employee(doc)
	result["overproduction_percentage"] = overproduction_percentage()
	return result


@frappe.whitelist()
def start_job_card(job_card_id: str) -> dict:
	check_manufacturing_permission()

	current_employee = get_current_employee()
	if not current_employee:
		frappe.throw(
			frappe._("No active Employee is linked to the current user."),
			frappe.PermissionError,
		)

	args = frappe._dict(
		job_card_id=job_card_id,
		start_time=now_datetime(),
		status="Work In Progress",
	)
	args.employees = [{"employee": current_employee}]

	doc = fetch_job_card(job_card_id)
	require_predecessors_met(doc.work_order)
	require_materials_in_wip(doc)
	make_time_log(args)
	return get_job_card(job_card_id)


@frappe.whitelist()
def pause_job_card(job_card_id: str, completed_qty: float = 0) -> dict:
	check_manufacturing_permission()

	doc = fetch_job_card(job_card_id)
	_, max_qty = production_qty_limits(doc.for_quantity)
	projected = projected_completed_qty(doc, completed_qty)
	if projected > max_qty:
		frappe.throw(
			frappe._("Completed quantity {0} cannot exceed {1}").format(flt(projected), flt(max_qty)),
			frappe.ValidationError,
		)

	make_time_log(
		frappe._dict(
			job_card_id=job_card_id,
			complete_time=now_datetime(),
			status="On Hold",
			completed_qty=flt(completed_qty),
		)
	)
	return get_job_card(job_card_id)


@frappe.whitelist()
def finish_job_card(job_card_id: str, completed_qty: float) -> dict:
	check_manufacturing_permission()

	doc = fetch_job_card(job_card_id)
	min_qty, max_qty = production_qty_limits(doc.for_quantity)
	projected = projected_completed_qty(doc, completed_qty)
	if projected < min_qty or projected > max_qty:
		frappe.throw(
			frappe._("Completed quantity {0} must be between {1} and {2}").format(
				flt(projected), flt(min_qty), flt(max_qty)
			),
			frappe.ValidationError,
		)

	make_time_log(
		frappe._dict(
			job_card_id=job_card_id,
			complete_time=now_datetime(),
			status="Complete",
			completed_qty=flt(completed_qty),
		)
	)

	with ignoring_user_permissions():
		doc = frappe.get_doc("Job Card", job_card_id)
		if doc.docstatus == 0:
			doc.flags.ignore_permissions = True
			completed = flt(doc.total_completed_qty)
			# Over the planned qty: raise Qty to Manufacture so submit can match it.
			# Under the planned qty: book the shortfall as process loss.
			if completed > flt(doc.for_quantity):
				doc.for_quantity = completed
			elif completed < flt(doc.for_quantity):
				doc.process_loss_qty = flt(doc.for_quantity) - completed
			doc.submit()

	return get_job_card(job_card_id)
