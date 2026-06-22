# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import time

import frappe
from frappe import _

from beam.beam.overrides.network_printer_settings import (
	check_network_printer_settings_read_permission,
	check_network_printer_settings_write_permission,
	cups_connection,
	is_local_cups_server,
	require_cups,
)

SESSION_CACHE_PREFIX = "printer_queue_session:"
SESSION_LEASE_SECONDS = 120
SESSION_LOOKBACK_SECONDS = 120
COMPLETED_JOBS_FETCH_LIMIT = 100

TERMINAL_JOB_STATES = {"completed", "cancelled", "aborted"}
ACTIVE_JOB_STATES = {"pending", "held", "processing", "stopped"}

JOB_STATE_LABELS = {
	3: "pending",
	4: "held",
	5: "processing",
	6: "stopped",
	7: "cancelled",
	8: "aborted",
	9: "completed",
}

JOB_ATTRIBUTES = [
	"job-id",
	"job-name",
	"job-state",
	"job-state-reasons",
	"job-originating-user-name",
	"job-printer-uri",
	"time-at-creation",
	"time-at-processing",
	"time-at-completed",
	"job-media-sheets",
	"job-media-sheets-completed",
]


def check_printer_queue_read_permission():
	check_network_printer_settings_read_permission()


def check_printer_queue_write_permission():
	check_network_printer_settings_write_permission()


def session_cache_key(task_id):
	return f"{SESSION_CACHE_PREFIX}{task_id}"


def watcher_cache_key(task_id):
	return session_cache_key(task_id)


def list_print_servers():
	rows = frappe.get_all(
		"Network Printer Settings",
		fields=["server_ip", "port"],
		order_by="server_ip asc, port asc",
	)
	servers = []
	seen = set()
	for row in rows:
		server_ip = row.server_ip or "localhost"
		port = int(row.port or 631)
		key = (server_ip, port)
		if key in seen:
			continue
		seen.add(key)
		servers.append({"server_ip": server_ip, "port": port})
	return servers


def get_print_servers():
	check_printer_queue_read_permission()
	return list_print_servers()


def print_server_label(server_ip, port):
	if is_local_cups_server(server_ip, port):
		return _("Local Print Server")
	return f"{server_ip}:{port}"


def printer_name_from_uri(printer_uri):
	if not printer_uri:
		return ""
	if printer_uri.endswith("/"):
		printer_uri = printer_uri[:-1]
	return printer_uri.rsplit("/", 1)[-1]


def normalize_job_state(state_value):
	if state_value is None:
		return "unknown"
	try:
		state_int = int(state_value)
	except (TypeError, ValueError):
		return str(state_value).lower()
	return JOB_STATE_LABELS.get(state_int, str(state_int))


def display_status_for_state(job_state):
	if job_state == "completed":
		return "printed"
	return job_state


def coerce_timestamp(value):
	if value is None:
		return None
	if isinstance(value, (list, tuple)):
		value = value[0] if value else None
	if value is None:
		return None
	try:
		return int(value)
	except (TypeError, ValueError):
		return None


def normalize_job(job_id, attrs, server_ip, port):
	creation = coerce_timestamp(attrs.get("time-at-creation"))
	job_state = normalize_job_state(attrs.get("job-state"))
	return {
		"job_id": int(job_id),
		"job_name": attrs.get("job-name") or attrs.get("job-name-orig") or "",
		"job_state": job_state,
		"display_status": display_status_for_state(job_state),
		"job_state_reasons": attrs.get("job-state-reasons") or [],
		"user": attrs.get("job-originating-user-name") or "",
		"printer": printer_name_from_uri(attrs.get("job-printer-uri") or ""),
		"printer_uri": attrs.get("job-printer-uri") or "",
		"server_ip": server_ip,
		"port": int(port),
		"server_label": print_server_label(server_ip, port),
		"time_at_creation": creation,
		"time_at_processing": coerce_timestamp(attrs.get("time-at-processing")),
		"time_at_completed": coerce_timestamp(attrs.get("time-at-completed")),
		"pages": attrs.get("job-media-sheets"),
		"pages_completed": attrs.get("job-media-sheets-completed"),
	}


def merge_job_rows(rows):
	merged = {}
	for row in rows:
		key = (row["server_ip"], row["port"], row["job_id"])
		existing = merged.get(key)
		if not existing or row.get("time_at_creation", 0) >= existing.get("time_at_creation", 0):
			merged[key] = row
	return list(merged.values())


def sort_timestamp(value):
	return value if value is not None else 0


def sort_job_rows(rows):
	def sort_key(row):
		is_active = row.get("job_state") in ACTIVE_JOB_STATES
		completed_at = sort_timestamp(row.get("time_at_completed"))
		if row.get("time_at_completed") is None:
			completed_at = sort_timestamp(row.get("time_at_creation"))
		created_at = sort_timestamp(row.get("time_at_creation"))
		return (is_active, completed_at, created_at, row["job_id"])

	rows.sort(key=sort_key, reverse=True)
	return rows


def job_row_cache_key(row):
	return f"{row['server_ip']}:{row['port']}:{row['job_id']}"


def job_finished_at(row):
	if row.get("time_at_completed") is not None:
		return row["time_at_completed"]
	if row.get("time_at_creation") is not None:
		return row["time_at_creation"]
	return None


def job_in_session_window(row, completed_since, allow_unknown_terminal=False):
	if row.get("job_state") not in TERMINAL_JOB_STATES:
		return True
	finished = job_finished_at(row)
	if finished is not None and finished >= completed_since:
		return True
	return allow_unknown_terminal and finished is None


def fetch_job_row(server_ip, port, job_id):
	conn = cups_connection(server_ip, port)
	attrs = conn.getJobAttributes(int(job_id), requested_attributes=JOB_ATTRIBUTES)
	if not attrs:
		return None
	return normalize_job(job_id, attrs, server_ip, port)


def fetch_jobs_for_server(
	server_ip,
	port,
	completed_since=None,
	include_completed=False,
	completed_limit=COMPLETED_JOBS_FETCH_LIMIT,
):
	conn = cups_connection(server_ip, port)
	active_jobs = conn.getJobs(
		which_jobs="not-completed",
		requested_attributes=JOB_ATTRIBUTES,
	)
	rows = []
	for job_id, attrs in (active_jobs or {}).items():
		rows.append(normalize_job(job_id, attrs, server_ip, port))

	if include_completed and completed_since is not None:
		completed_jobs = conn.getJobs(
			which_jobs="completed",
			limit=completed_limit,
			requested_attributes=JOB_ATTRIBUTES,
		)
		for job_id, attrs in (completed_jobs or {}).items():
			row = normalize_job(job_id, attrs, server_ip, port)
			if job_in_session_window(row, completed_since, allow_unknown_terminal=True):
				rows.append(row)

	return sort_job_rows(merge_job_rows(rows))


def get_session_state(task_id):
	return frappe.cache.get_value(session_cache_key(task_id), expires=True) or {}


def get_watcher_state(task_id):
	return get_session_state(task_id)


def merge_session_jobs(jobs, session_jobs):
	if not session_jobs:
		return jobs
	merged = {(row["server_ip"], row["port"], row["job_id"]): row for row in jobs}
	for row in session_jobs.values():
		key = (row["server_ip"], row["port"], row["job_id"])
		if key in merged:
			continue
		merged[key] = row
	return list(merged.values())


def apply_session_state(task_id, current_jobs):
	state = get_session_state(task_id)
	if not state:
		return current_jobs

	completed_since = state.get("completed_since")
	session_jobs = dict(state.get("session_jobs") or {})
	seen_active = dict(state.get("seen_active") or {})
	current_by_key = {job_row_cache_key(row): row for row in current_jobs}
	current_active_keys = {
		key for key, row in current_by_key.items() if row.get("job_state") in ACTIVE_JOB_STATES
	}

	for key in current_active_keys:
		seen_active[key] = current_by_key[key]

	for key, prev_row in list(seen_active.items()):
		if key in current_active_keys:
			continue
		if key in session_jobs:
			del seen_active[key]
			continue
		if key in current_by_key:
			row = current_by_key[key]
			if row.get("job_state") in TERMINAL_JOB_STATES:
				session_jobs[key] = row
			del seen_active[key]
			continue
		try:
			row = fetch_job_row(prev_row["server_ip"], prev_row["port"], prev_row["job_id"])
		except Exception:
			row = None
		if row and row.get("job_state") in TERMINAL_JOB_STATES:
			session_jobs[key] = row
			del seen_active[key]
		elif row:
			seen_active[key] = row
		else:
			session_jobs[key] = {
				**prev_row,
				"job_state": "completed",
				"display_status": "printed",
				"time_at_completed": int(time.time()),
			}
			del seen_active[key]

	for key, row in current_by_key.items():
		if row.get("job_state") in TERMINAL_JOB_STATES:
			session_jobs[key] = row

	state["session_jobs"] = session_jobs
	state["seen_active"] = seen_active
	frappe.cache.set_value(
		session_cache_key(task_id),
		state,
		expires_in_sec=SESSION_LEASE_SECONDS,
	)
	return merge_session_jobs(current_jobs, session_jobs)


def collect_printer_jobs_snapshot(task_id=None):
	completed_since = None
	include_completed = False
	if task_id:
		state = get_session_state(task_id)
		completed_since = state.get("completed_since")
		include_completed = bool(state.get("fetch_completed_once"))

	jobs = []
	errors = []
	for server in list_print_servers():
		try:
			jobs.extend(
				fetch_jobs_for_server(
					server["server_ip"],
					server["port"],
					completed_since,
					include_completed=include_completed,
				)
			)
		except Exception as exc:
			errors.append(
				{
					"server_ip": server["server_ip"],
					"port": server["port"],
					"server_label": print_server_label(server["server_ip"], server["port"]),
					"message": str(exc),
				}
			)

	result_jobs = sort_job_rows(merge_job_rows(jobs))
	if task_id:
		if include_completed:
			state = get_session_state(task_id)
			if state and state.get("fetch_completed_once"):
				state["fetch_completed_once"] = False
				frappe.cache.set_value(
					session_cache_key(task_id),
					state,
					expires_in_sec=SESSION_LEASE_SECONDS,
				)
		result_jobs = apply_session_state(task_id, result_jobs)
	return {
		"jobs": sort_job_rows(merge_job_rows(result_jobs)),
		"errors": errors,
		"completed_since": completed_since,
	}


def get_printer_jobs_snapshot():
	check_printer_queue_read_permission()
	return collect_printer_jobs_snapshot()


def set_session_lease(task_id, user, session_started_at=None, completed_since=None):
	existing = get_session_state(task_id)
	state = {
		"user": user,
		"task_id": task_id,
		"session_started_at": session_started_at or existing.get("session_started_at"),
		"completed_since": (
			completed_since if completed_since is not None else existing.get("completed_since")
		),
		"fetch_completed_once": (
			True if session_started_at is not None else existing.get("fetch_completed_once", False)
		),
		"session_jobs": existing.get("session_jobs") or {},
		"seen_active": existing.get("seen_active") or {},
	}
	frappe.cache.set_value(
		session_cache_key(task_id),
		state,
		expires_in_sec=SESSION_LEASE_SECONDS,
	)
	return state


def set_watcher_lease(task_id, user, session_started_at=None, completed_since=None):
	return set_session_lease(task_id, user, session_started_at, completed_since)


def session_lease_active(task_id):
	return bool(frappe.cache.get_value(session_cache_key(task_id), expires=True))


def watcher_lease_active(task_id):
	return session_lease_active(task_id)


@frappe.whitelist()
def start_printer_queue_watcher():
	check_printer_queue_read_permission()
	task_id = frappe.generate_hash(length=12)
	user = frappe.session.user
	session_started_at = int(time.time())
	completed_since = session_started_at - SESSION_LOOKBACK_SECONDS
	set_session_lease(
		task_id,
		user,
		session_started_at=session_started_at,
		completed_since=completed_since,
	)
	snapshot = collect_printer_jobs_snapshot(task_id=task_id)
	return {"task_id": task_id, **snapshot}


@frappe.whitelist()
def poll_printer_queue(task_id):
	check_printer_queue_read_permission()
	if not task_id or not session_lease_active(task_id):
		return {"expired": True, "task_id": task_id}
	set_session_lease(task_id, frappe.session.user)
	snapshot = collect_printer_jobs_snapshot(task_id=task_id)
	return {"expired": False, "task_id": task_id, **snapshot}


@frappe.whitelist()
def stop_printer_queue_watcher(task_id):
	check_printer_queue_read_permission()
	if not task_id:
		return {"stopped": False}
	frappe.cache.delete_value(session_cache_key(task_id))
	return {"stopped": True, "task_id": task_id}


@frappe.whitelist()
def cancel_printer_job(server_ip, port, job_id):
	check_printer_queue_write_permission()
	conn = cups_connection(server_ip, int(port))
	cups = require_cups()
	try:
		conn.cancelJob(int(job_id))
	except cups.IPPError as exc:
		frappe.throw(_("Could not cancel print job: {0}").format(exc))
	except Exception as exc:
		frappe.throw(_("Could not cancel print job: {0}").format(exc))
	return {"cancelled": True, "job_id": int(job_id)}
