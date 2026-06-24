# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import time
from unittest.mock import Mock, patch

import frappe
import pytest

from beam.beam import printer_queue as pq


TEST_PRINT_SERVER = {"server_ip": "localhost", "port": 631}


def mock_cups_connection(get_jobs=None):
	mock_conn = Mock()
	mock_conn.getJobs.return_value = get_jobs or {}
	mock_conn.cancelJob = Mock()
	return mock_conn


@pytest.mark.order(180)
def test_get_printer_jobs_snapshot_returns_active_jobs_only():
	doc_name = "Printer Queue Snapshot Test"
	if frappe.db.exists("Network Printer Settings", doc_name):
		frappe.delete_doc("Network Printer Settings", doc_name)

	frappe.get_doc(
		{
			"doctype": "Network Printer Settings",
			"name": doc_name,
			"server_ip": "localhost",
			"port": 631,
			"printer_name": "ZD621",
		}
	).insert()

	def get_jobs(which_jobs="not-completed", **kwargs):
		if which_jobs == "not-completed":
			return {
				42: {
					"job-id": 42,
					"job-name": "Invoice-001",
					"job-state": 3,
					"job-originating-user-name": "Administrator",
					"job-printer-uri": "ipp://localhost/printers/ZD621",
					"time-at-creation": 1_700_000_000,
					"job-media-sheets": 2,
				}
			}
		if which_jobs == "completed":
			return {
				41: {
					"job-id": 41,
					"job-name": "Label-001",
					"job-state": 9,
					"job-originating-user-name": "Administrator",
					"job-printer-uri": "ipp://localhost/printers/ZD621",
					"time-at-creation": 1_699_999_000,
					"time-at-completed": 1_700_000_050,
				}
			}
		return {}

	mock_conn = mock_cups_connection()
	mock_conn.getJobs.side_effect = get_jobs
	with (
		patch.object(pq, "cups_connection", return_value=mock_conn),
		patch.object(pq, "list_print_servers", return_value=[TEST_PRINT_SERVER]),
	):
		result = pq.get_printer_jobs_snapshot()

	assert len(result["jobs"]) == 1
	pending = result["jobs"][0]
	assert pending["job_state"] == "pending"
	assert pending["job_id"] == 42
	assert pending["printer"] == "ZD621"
	mock_conn.getJobs.assert_called_once_with(
		which_jobs="not-completed",
		requested_attributes=pq.JOB_ATTRIBUTES,
	)


@pytest.mark.order(182)
def test_session_snapshot_includes_recent_completed_jobs():
	doc_name = "Printer Queue Session Test"
	if frappe.db.exists("Network Printer Settings", doc_name):
		frappe.delete_doc("Network Printer Settings", doc_name)

	frappe.get_doc(
		{
			"doctype": "Network Printer Settings",
			"name": doc_name,
			"server_ip": "localhost",
			"port": 631,
			"printer_name": "ZD621",
		}
	).insert()

	task_id = "testsnapshot01"
	completed_since = 1_700_000_000
	pq.set_watcher_lease(
		task_id,
		frappe.session.user,
		session_started_at=completed_since + pq.SESSION_LOOKBACK_SECONDS,
		completed_since=completed_since,
	)

	def get_jobs(which_jobs="not-completed", **kwargs):
		if which_jobs == "not-completed":
			return {
				42: {
					"job-id": 42,
					"job-name": "Invoice-001",
					"job-state": 3,
					"job-originating-user-name": "Administrator",
					"job-printer-uri": "ipp://localhost/printers/ZD621",
					"time-at-creation": 1_700_000_100,
				}
			}
		if which_jobs == "completed":
			return {
				41: {
					"job-id": 41,
					"job-name": "Recent Label",
					"job-state": 9,
					"job-originating-user-name": "Administrator",
					"job-printer-uri": "ipp://localhost/printers/ZD621",
					"time-at-creation": 1_699_999_900,
					"time-at-completed": completed_since + 30,
				},
				40: {
					"job-id": 40,
					"job-name": "Old Label",
					"job-state": 9,
					"job-originating-user-name": "Administrator",
					"job-printer-uri": "ipp://localhost/printers/ZD621",
					"time-at-creation": 1_699_000_000,
					"time-at-completed": completed_since - 30,
				},
			}
		return {}

	mock_conn = mock_cups_connection()
	mock_conn.getJobs.side_effect = get_jobs
	with (
		patch.object(pq, "cups_connection", return_value=mock_conn),
		patch.object(pq, "list_print_servers", return_value=[TEST_PRINT_SERVER]),
	):
		result = pq.collect_printer_jobs_snapshot(task_id=task_id)

	assert len(result["jobs"]) == 2
	job_ids = {job["job_id"] for job in result["jobs"]}
	assert job_ids == {41, 42}
	printed = next(job for job in result["jobs"] if job["job_id"] == 41)
	assert printed["display_status"] == "printed"
	assert result["completed_since"] == completed_since
	completed_calls = [
		call for call in mock_conn.getJobs.call_args_list if call.kwargs.get("which_jobs") == "completed"
	]
	assert completed_calls
	assert completed_calls[0].kwargs.get("limit") == pq.COMPLETED_JOBS_FETCH_LIMIT


@pytest.mark.order(184)
def test_session_tracks_jobs_that_finish_between_polls():
	task_id = "testsnapshot02"
	completed_since = 1_700_000_000
	pq.set_watcher_lease(
		task_id,
		frappe.session.user,
		session_started_at=completed_since + pq.SESSION_LOOKBACK_SECONDS,
		completed_since=completed_since,
	)
	state = pq.get_watcher_state(task_id)
	state["fetch_completed_once"] = False
	frappe.cache.set_value(
		pq.watcher_cache_key(task_id),
		state,
		expires_in_sec=pq.SESSION_LEASE_SECONDS,
	)

	active_row = {
		"job_id": 55,
		"job_name": "PDF Test",
		"job_state": "processing",
		"display_status": "processing",
		"job_state_reasons": [],
		"user": "Administrator",
		"printer": "PDF",
		"printer_uri": "ipp://localhost/printers/PDF",
		"server_ip": "localhost",
		"port": 631,
		"server_label": "Local Print Server",
		"time_at_creation": completed_since + 60,
		"time_at_processing": completed_since + 61,
		"time_at_completed": None,
		"pages": 1,
		"pages_completed": 0,
	}
	completed_row = {
		**active_row,
		"job_state": "completed",
		"display_status": "printed",
		"time_at_completed": completed_since + 62,
	}

	mock_conn = mock_cups_connection(get_jobs={})
	with (
		patch.object(pq, "cups_connection", return_value=mock_conn),
		patch.object(pq, "list_print_servers", return_value=[{"server_ip": "localhost", "port": 631}]),
		patch.object(pq, "fetch_job_row", return_value=completed_row),
	):
		pq.apply_session_state(task_id, [active_row])
		result = pq.collect_printer_jobs_snapshot(task_id=task_id)

	assert any(job["job_id"] == 55 and job["display_status"] == "printed" for job in result["jobs"])
	pq.stop_printer_queue_watcher(task_id)


@pytest.mark.order(186)
def test_start_printer_queue_session_does_not_enqueue():
	mock_conn = mock_cups_connection()
	with (
		patch("frappe.enqueue") as mock_enqueue,
		patch.object(pq, "cups_connection", return_value=mock_conn),
		patch.object(pq, "list_print_servers", return_value=[TEST_PRINT_SERVER]),
	):
		result = pq.start_printer_queue_watcher()

	assert result["task_id"]
	mock_enqueue.assert_not_called()
	pq.stop_printer_queue_watcher(result["task_id"])


@pytest.mark.order(188)
def test_poll_printer_queue_refreshes_session():
	task_id = "testpoll01"
	pq.set_session_lease(task_id, frappe.session.user, session_started_at=int(time.time()))
	assert pq.session_lease_active(task_id)

	mock_conn = mock_cups_connection(
		get_jobs={
			7: {
				"job-id": 7,
				"job-name": "Label-001",
				"job-state": 5,
				"job-originating-user-name": "Administrator",
				"job-printer-uri": "ipp://localhost/printers/ZD621",
				"time-at-creation": 1_700_000_100,
			}
		}
	)
	with (
		patch.object(pq, "cups_connection", return_value=mock_conn),
		patch.object(pq, "list_print_servers", return_value=[TEST_PRINT_SERVER]),
	):
		result = pq.poll_printer_queue(task_id)

	assert result["expired"] is False
	assert result["task_id"] == task_id
	assert result["jobs"][0]["job_id"] == 7
	assert pq.session_lease_active(task_id)
	pq.stop_printer_queue_watcher(task_id)


@pytest.mark.order(190)
def test_poll_printer_queue_expired_session():
	result = pq.poll_printer_queue("missing-session")
	assert result["expired"] is True


@pytest.mark.order(192)
def test_cancel_printer_job():
	mock_conn = mock_cups_connection()
	with patch.object(pq, "cups_connection", return_value=mock_conn):
		result = pq.cancel_printer_job("localhost", 631, 99)

	assert result["cancelled"] is True
	mock_conn.cancelJob.assert_called_once_with(99)


@pytest.mark.order(194)
def test_start_and_stop_printer_queue_session_lease():
	task_id = "testsession01"
	pq.set_session_lease(task_id, frappe.session.user)
	assert pq.session_lease_active(task_id)

	pq.stop_printer_queue_watcher(task_id)
	assert not pq.session_lease_active(task_id)


@pytest.mark.order(196)
def test_apply_session_state_keeps_still_active_job_in_seen_active():
	"""A job still processing on CUPS stays in seen_active instead of session history."""
	task_id = "testsnapshot03"
	completed_since = 1_700_000_000
	pq.set_watcher_lease(
		task_id,
		frappe.session.user,
		session_started_at=completed_since + pq.SESSION_LOOKBACK_SECONDS,
		completed_since=completed_since,
	)

	active_row = {
		"job_id": 56,
		"job_name": "Kitchen Label",
		"job_state": "processing",
		"display_status": "processing",
		"job_state_reasons": [],
		"user": "Administrator",
		"printer": "ZD621",
		"printer_uri": "ipp://localhost/printers/ZD621",
		"server_ip": "localhost",
		"port": 631,
		"server_label": "Local Print Server",
		"time_at_creation": completed_since + 60,
		"time_at_processing": completed_since + 61,
		"time_at_completed": None,
		"pages": 1,
		"pages_completed": 0,
	}
	cache_key = pq.job_row_cache_key(active_row)

	pq.apply_session_state(task_id, [active_row])
	state = pq.get_watcher_state(task_id)
	assert cache_key in state["seen_active"]

	still_active_row = {**active_row, "job_state": "processing", "display_status": "processing"}
	with patch.object(pq, "fetch_job_row", return_value=still_active_row):
		pq.apply_session_state(task_id, [])

	state = pq.get_watcher_state(task_id)
	assert cache_key in state["seen_active"]
	assert cache_key not in state["session_jobs"]
	pq.stop_printer_queue_watcher(task_id)


@pytest.mark.order(198)
def test_job_in_session_window_treats_epoch_timestamp_as_recent():
	row = {
		"job_state": "completed",
		"time_at_creation": 0,
		"time_at_completed": 0,
	}
	assert pq.job_in_session_window(row, completed_since=0) is True


@pytest.mark.order(200)
def test_printer_queue_read_permission_required():
	with pytest.raises(frappe.exceptions.PermissionError):
		frappe.set_user("Guest")
		try:
			pq.get_printer_jobs_snapshot()
		finally:
			frappe.set_user("Administrator")
