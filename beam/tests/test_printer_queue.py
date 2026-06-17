# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

from unittest.mock import Mock, patch

import frappe
import pytest

from beam.beam import printer_queue as pq


TEST_PRINT_SERVER = {"server_ip": "localhost", "port": 631}


def mock_cups_connection(
	get_jobs=None,
	create_subscription=None,
	get_notifications=None,
	cancel_subscription=None,
):
	mock_conn = Mock()
	mock_conn.getJobs.return_value = get_jobs or {}
	mock_conn.createSubscription.return_value = (
		create_subscription if create_subscription is not None else 1
	)
	mock_conn.getNotifications.return_value = get_notifications or []
	mock_conn.cancelSubscription = cancel_subscription or Mock()
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
		expires_in_sec=pq.WATCHER_LEASE_SECONDS,
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
def test_start_and_stop_printer_queue_watcher_lease():
	task_id = "testwatcher01"
	pq.set_watcher_lease(task_id, frappe.session.user)
	assert pq.watcher_lease_active(task_id)

	pq.stop_printer_queue_watcher(task_id)
	assert not pq.watcher_lease_active(task_id)


@pytest.mark.order(132)
def test_notification_job_ids_reads_cups_event_dict():
	notifications = {
		"notify-get-interval": 60,
		"events": [{"notification-attributes": {"job-id": 99, "job-state": 9}}],
	}
	assert pq.notification_job_ids(notifications) == {99}


@pytest.mark.order(188)
def test_watch_printer_queues_publishes_updates():
	task_id = "testwatcher02"
	user = frappe.session.user
	pq.set_watcher_lease(task_id, user)

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
		},
		get_notifications={"events": [{"notification-attributes": {"job-id": 7, "job-state": 5}}]},
	)
	mock_conn.getJobs.side_effect = lambda which_jobs="not-completed", **kwargs: (
		mock_conn.getJobs.return_value if which_jobs == "not-completed" else {}
	)

	published = []

	def capture_publish(event, message=None, **kwargs):
		if event == "printer_queue_update":
			published.append(message)

	with (
		patch.object(pq, "cups_connection", return_value=mock_conn),
		patch.object(pq, "list_print_servers", return_value=[TEST_PRINT_SERVER]),
		patch.object(pq, "watcher_lease_active", side_effect=[True, True, False]),
		patch("frappe.publish_realtime", side_effect=capture_publish),
		patch.object(pq, "time") as mock_time,
	):
		mock_time.sleep = Mock()
		pq.watch_printer_queues(task_id, user)

	assert published
	assert published[0]["task_id"] == task_id
	assert published[0]["jobs"][0]["job_id"] == 7
	mock_conn.cancelSubscription.assert_called_once_with(1)


@pytest.mark.order(190)
def test_cancel_printer_job():
	mock_conn = mock_cups_connection()
	with patch.object(pq, "cups_connection", return_value=mock_conn):
		result = pq.cancel_printer_job("localhost", 631, 99)

	assert result["cancelled"] is True
	mock_conn.cancelJob.assert_called_once_with(99)


@pytest.mark.order(194)
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


@pytest.mark.order(196)
def test_job_in_session_window_treats_epoch_timestamp_as_recent():
	row = {
		"job_state": "completed",
		"time_at_creation": 0,
		"time_at_completed": 0,
	}
	assert pq.job_in_session_window(row, completed_since=0) is True


@pytest.mark.order(198)
def test_watch_printer_queues_recreates_subscription_after_failures():
	task_id = "testwatcher03"
	user = frappe.session.user
	pq.set_watcher_lease(task_id, user)

	mock_conn = mock_cups_connection(get_jobs={})
	mock_conn.getNotifications.side_effect = RuntimeError("subscription expired")
	mock_conn.createSubscription.side_effect = [1, 2]

	with (
		patch.object(pq, "cups_connection", return_value=mock_conn),
		patch.object(pq, "list_print_servers", return_value=[TEST_PRINT_SERVER]),
		patch.object(
			pq,
			"watcher_lease_active",
			side_effect=[True] * (2 + pq.SUBSCRIPTION_FAILURE_THRESHOLD) + [False],
		),
		patch.object(pq, "collect_printer_jobs_snapshot", return_value={"jobs": [], "errors": []}),
		patch("frappe.publish_realtime"),
		patch.object(pq, "time") as mock_time,
	):
		mock_time.sleep = Mock()
		pq.watch_printer_queues(task_id, user)

	assert mock_conn.createSubscription.call_count == 2
	mock_conn.cancelSubscription.assert_any_call(1)
	mock_conn.cancelSubscription.assert_any_call(2)
	pq.stop_printer_queue_watcher(task_id)


@pytest.mark.order(192)
def test_printer_queue_read_permission_required():
	with pytest.raises(frappe.exceptions.PermissionError):
		frappe.set_user("Guest")
		try:
			pq.get_printer_jobs_snapshot()
		finally:
			frappe.set_user("Administrator")
