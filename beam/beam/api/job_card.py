# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import json

import frappe
from erpnext.manufacturing.doctype.job_card.job_card import make_time_log
from frappe import _
from frappe.utils import flt, now_datetime


def _get_assigned_users(job_card_doc):
	if not job_card_doc._assign:
		return []

	try:
		return json.loads(job_card_doc._assign)
	except Exception:
		return []


def _ensure_job_card_is_assigned_to_current_user(job_card_doc):
	if frappe.session.user == "Administrator":
		return

	assigned_users = _get_assigned_users(job_card_doc)
	if assigned_users and frappe.session.user not in assigned_users:
		frappe.throw(_("This Job Card is not assigned to the current user."), frappe.PermissionError)


def _get_employee_for_current_user():
	employee = frappe.db.get_value(
		"Employee",
		{"user_id": frappe.session.user, "status": "Active"},
		"name",
	)

	if not employee:
		frappe.throw(
			_("No active Employee linked to user {0}.").format(frappe.session.user),
			frappe.ValidationError,
		)

	return employee


def _get_job_card(job_card_id):
	job_card = frappe.get_doc("Job Card", job_card_id)
	_ensure_job_card_is_assigned_to_current_user(job_card)
	return job_card


@frappe.whitelist()
def start_job_card(job_card_id):
	job_card = _get_job_card(job_card_id)
	employee = _get_employee_for_current_user()

	args = {
		"job_card_id": job_card.name,
		"start_time": now_datetime(),
		"status": "Work In Progress",
	}
	if employee:
		args["employees"] = [{"employee": employee}]

	make_time_log(args)

	return frappe.get_doc("Job Card", job_card.name)


@frappe.whitelist()
def pause_job_card(job_card_id):
	job_card = _get_job_card(job_card_id)

	args = {
		"job_card_id": job_card.name,
		"complete_time": now_datetime(),
		"status": "On Hold",
		"completed_qty": 0,
	}
	make_time_log(args)

	return frappe.get_doc("Job Card", job_card.name)


@frappe.whitelist()
def finish_job_card(job_card_id, completed_qty=None):
	job_card = _get_job_card(job_card_id)

	remaining_qty = max((job_card.for_quantity or 0) - (job_card.total_completed_qty or 0), 0)

	if completed_qty is None:
		completed_qty = remaining_qty

	completed_qty = flt(completed_qty)
	if completed_qty <= 0:
		frappe.throw(_("Completed quantity must be greater than zero."), frappe.ValidationError)

	if completed_qty > remaining_qty:
		frappe.throw(
			_("Completed quantity cannot be greater than remaining quantity ({0}).").format(remaining_qty),
			frappe.ValidationError,
		)

	has_open_time_log = any(not row.to_time for row in (job_card.time_logs or []))
	complete_time = now_datetime()

	if not has_open_time_log:
		make_time_log(
			{
				"job_card_id": job_card.name,
				"start_time": complete_time,
				"status": "Work In Progress",
			}
		)

	args = {
		"job_card_id": job_card.name,
		"complete_time": complete_time,
		"status": "Complete",
		"completed_qty": completed_qty,
	}
	make_time_log(args)
	job_card = frappe.get_doc("Job Card", job_card.name)

	if job_card.docstatus == 0:
		job_card.submit()

	return frappe.get_doc("Job Card", job_card.name)
