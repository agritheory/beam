# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe


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


def fetch_job_card(job_card_id: str):
	frappe.flags.ignore_user_permissions = True
	try:
		doc = frappe.get_doc("Job Card", job_card_id)
	finally:
		frappe.flags.ignore_user_permissions = False
	return doc


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
	frappe.flags.ignore_user_permissions = True
	try:
		doc = frappe.get_doc("Job Card", args.job_card_id)
		doc.flags.ignore_permissions = True
		doc.validate_sequence_id()
		ensure_employee_on_job_card(doc, args)
		doc.add_time_log(args)
	finally:
		frappe.flags.ignore_user_permissions = False


def ensure_employee_on_job_card(doc, args: frappe._dict) -> None:
	"""
	ERPNext only populates the Job Card employee field when it is empty (first start).
	When a second employee picks up paused work, we add them here so the field always
	reflects every participant.
	"""
	employees = args.get("employees") or []
	if isinstance(employees, str):
		import json

		employees = json.loads(employees)

	existing = {row.employee for row in doc.employee if row.employee}
	for entry in employees:
		emp = entry.get("employee")
		if emp and emp not in existing:
			doc.append("employee", {"employee": emp, "completed_qty": 0.0})
			existing.add(emp)


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
		start_time=frappe.utils.now_datetime(),
		status="Work In Progress",
	)
	args.employees = [{"employee": current_employee}]

	make_time_log(args)
	return get_job_card(job_card_id)


@frappe.whitelist()
def pause_job_card(job_card_id: str, completed_qty: float = 0) -> dict:
	check_manufacturing_permission()

	make_time_log(
		frappe._dict(
			job_card_id=job_card_id,
			complete_time=frappe.utils.now_datetime(),
			status="On Hold",
			completed_qty=frappe.utils.flt(completed_qty),
		)
	)
	return get_job_card(job_card_id)


@frappe.whitelist()
def finish_job_card(job_card_id: str, completed_qty: float) -> dict:
	check_manufacturing_permission()

	make_time_log(
		frappe._dict(
			job_card_id=job_card_id,
			complete_time=frappe.utils.now_datetime(),
			status="Complete",
			completed_qty=frappe.utils.flt(completed_qty),
		)
	)

	frappe.flags.ignore_user_permissions = True
	try:
		doc = frappe.get_doc("Job Card", job_card_id)
		if doc.docstatus == 0:
			doc.flags.ignore_permissions = True
			doc.submit()
	finally:
		frappe.flags.ignore_user_permissions = False

	return get_job_card(job_card_id)
