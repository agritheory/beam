# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

from unittest.mock import Mock, patch

import frappe
import pytest

from beam.beam.overrides import network_printer_settings as nps


def mock_cups_connection(get_devices=None, get_printers=None, get_ppds=None):
	printers = get_printers or {}
	mock_conn = Mock()
	mock_conn.getDevices.return_value = get_devices or {}
	mock_conn.getPrinters.return_value = printers
	mock_conn.getPPDs.return_value = get_ppds or {}
	mock_conn.addPrinter = Mock()
	mock_conn.enablePrinter = Mock()
	mock_conn.acceptJobs = Mock()
	mock_conn.deletePrinter = Mock()
	mock_conn.setPrinterDevice = Mock()
	mock_conn.setPrinterLocation = Mock()
	mock_conn.disablePrinter = Mock()
	mock_conn.rejectJobs = Mock()
	mock_conn.printTestPage = Mock(return_value=1)
	mock_conn.printFile = Mock(return_value=1)
	mock_conn.getOptions = Mock(return_value={})
	mock_conn.setPrinterOptions = Mock()

	def get_printer_attributes(name):
		attrs = dict(printers.get(name, {}))
		attrs.setdefault("printer-is-accepting-jobs", True)
		return attrs

	mock_conn.getPrinterAttributes.side_effect = get_printer_attributes
	return mock_conn


@pytest.mark.order(140)
def test_wizard_blocks_duplicate_cups_queue():
	"""Creating ZD621 fails when that queue already exists on the Chelsea print server."""
	mock_conn = mock_cups_connection(
		get_printers={
			"ZD621": {
				"printer-make-and-model": "Local Raw Printer",
				"printer-location": "Chelsea Receiving",
				"device-uri": "socket://192.168.1.50:9100",
			}
		}
	)
	with patch.object(nps, "cups_connection", return_value=mock_conn):
		result = nps.validate_wizard_selection(
			"localhost",
			631,
			"create",
			printer_name="ZD621",
			device_uri="socket://192.168.1.50:9100",
			kind="device",
		)
	assert result["allowed"] is False
	assert "ZD621" in result["message"]


@pytest.mark.order(142)
def test_wizard_blocks_queue_already_linked():
	"""ZD621 cannot be linked again when Chelsea Receiving Labels already owns it."""
	doc_name = "Chelsea Receiving Labels"
	if not frappe.db.exists("Network Printer Settings", doc_name):
		frappe.get_doc(
			{
				"doctype": "Network Printer Settings",
				"name": doc_name,
				"server_ip": "localhost",
				"port": 631,
				"printer_name": "ZD621",
			}
		).insert()

	mock_conn = mock_cups_connection(
		get_printers={
			"ZD621": {
				"printer-make-and-model": "Local Raw Printer",
				"printer-location": "Chelsea Receiving",
				"device-uri": "socket://192.168.1.50:9100",
			}
		}
	)
	with patch.object(nps, "cups_connection", return_value=mock_conn):
		result = nps.validate_wizard_selection(
			"localhost",
			631,
			"link",
			printer_name="ZD621",
			kind="queue",
		)
	assert result["allowed"] is False
	assert doc_name in result["message"]


@pytest.mark.order(144)
def test_wizard_links_existing_unlinked_queue():
	"""Legacy vRAW on CUPS becomes Chelsea Raw Labels in ERPNext without addPrinter."""
	queue_name = "vRAW"
	nps_name = "Chelsea Raw Labels"
	if frappe.db.exists("Network Printer Settings", nps_name):
		frappe.delete_doc("Network Printer Settings", nps_name)
	for linked_name in frappe.get_all(
		"Network Printer Settings",
		filters={"printer_name": queue_name},
		pluck="name",
	):
		frappe.delete_doc("Network Printer Settings", linked_name)

	mock_conn = mock_cups_connection(
		get_printers={
			queue_name: {
				"printer-make-and-model": "Local Raw Printer",
				"printer-location": "Chelsea Receiving",
				"device-uri": "socket://192.168.1.51:9100",
			}
		}
	)
	existing = set(frappe.get_all("Network Printer Settings", pluck="name"))
	with patch.object(nps, "cups_connection", return_value=mock_conn):
		doc = nps.link_existing_printer(
			nps_name,
			"localhost",
			631,
			queue_name,
			printer_location="Chelsea Receiving",
			printer_type="Label / RAW",
		)
	assert doc["name"] == nps_name
	assert doc["printer_name"] == queue_name
	mock_conn.addPrinter.assert_not_called()
	created = set(frappe.get_all("Network Printer Settings", pluck="name")) - existing
	assert nps_name in created


@pytest.mark.order(146)
def test_get_wizard_devices_marks_configured_and_sorts_unconfigured_first():
	"""Receiving Printer is configured; ZD621 is not and appears first in discovery."""
	receiving_name = "BEAM Wizard Sort Receiving"
	receiving_queue = "BEAM_WIZARD_RECEIVING"
	unconfigured_queue = "BEAM_WIZARD_ZD621"
	for doc_name in (receiving_name, "BEAM Wizard Sort Unconfigured"):
		if frappe.db.exists("Network Printer Settings", doc_name):
			frappe.delete_doc("Network Printer Settings", doc_name)

	frappe.get_doc(
		{
			"doctype": "Network Printer Settings",
			"name": receiving_name,
			"server_ip": "localhost",
			"port": 631,
			"printer_name": receiving_queue,
		}
	).insert()

	mock_conn = mock_cups_connection(
		get_printers={
			receiving_queue: {
				"printer-make-and-model": "Office Printer",
				"printer-location": "Kitchen",
				"device-uri": "socket://192.168.1.10:9100",
			},
			unconfigured_queue: {
				"printer-make-and-model": "Local Raw Printer",
				"printer-location": "Chelsea Receiving",
				"device-uri": "socket://192.168.1.50:9100",
			},
		}
	)
	with patch.object(nps, "cups_connection", return_value=mock_conn):
		entries = nps.get_wizard_devices("localhost", 631)

	queue_entries = [entry for entry in entries if entry["kind"] == "queue"]
	unconfigured = next(entry for entry in queue_entries if entry["value"] == unconfigured_queue)
	receiving = next(entry for entry in queue_entries if entry["value"] == receiving_queue)
	assert unconfigured["configured"] is False
	assert receiving["configured"] is True
	assert receiving["nps_name"] == receiving_name
	assert queue_entries.index(unconfigured) < queue_entries.index(receiving)


@pytest.mark.order(148)
def test_wizard_creates_queue_and_nps():
	"""Stock Manager adds Chelsea Receiving Labels as a new ZD621 raw queue."""
	nps_name = "Chelsea Receiving Labels"
	if frappe.db.exists("Network Printer Settings", nps_name):
		frappe.delete_doc("Network Printer Settings", nps_name)

	mock_conn = mock_cups_connection(get_printers={})
	existing = set(frappe.get_all("Network Printer Settings", pluck="name"))
	reachable_uri = {
		"host": "192.168.1.50",
		"port": 9100,
		"ping_result": {"reachable": True, "host": "192.168.1.50", "message": "ok"},
		"socket_reachable": True,
		"message": "ok",
		"warnings": [],
	}
	with patch.object(nps, "cups_connection", return_value=mock_conn), patch.object(
		nps, "validate_device_uri", return_value=reachable_uri
	):
		doc = nps.create_printer_queue(
			nps_name,
			"localhost",
			631,
			"ZD621",
			"socket://192.168.1.50:9100",
			ppdname="raw",
			printer_location="Chelsea Receiving",
			printer_type="Label / RAW",
		)

	assert doc["printer_location"] == "Chelsea Receiving"
	assert doc["printer_type"] == "Label / RAW"
	mock_conn.addPrinter.assert_called_once()
	created = set(frappe.get_all("Network Printer Settings", pluck="name")) - existing
	assert nps_name in created


@pytest.mark.order(150)
def test_wizard_rejects_usb_uri():
	"""USB printers are rejected for Chelsea dock setup."""
	with pytest.raises(frappe.ValidationError, match="USB"):
		nps.reject_usb_uri("usb://Zebra/ZD621")


@pytest.mark.order(152)
def test_get_ppds_filters_by_query():
	"""PPD browser returns Zebra drivers when searching for ZD621."""
	mock_conn = mock_cups_connection(
		get_ppds={
			"raw": {"ppd-make-and-model": "Raw Queue", "ppd-make": "Generic"},
			"zebra.ppd": {"ppd-make-and-model": "Zebra ZD621", "ppd-make": "Zebra"},
			"everywhere": {"ppd-make-and-model": "Generic IPP Everywhere", "ppd-make": "Generic"},
		}
	)
	with patch.object(nps, "cups_connection", return_value=mock_conn):
		results = nps.get_ppds("localhost", 631, query="zebra")
	assert len(results) == 1
	assert results[0]["value"] == "zebra.ppd"


@pytest.mark.order(154)
def test_configure_printer_updates_cups_queue():
	"""Administrator updates Chelsea Receiving Labels with a new socket URI."""
	doc_name = "Chelsea Receiving Labels Configure"
	if frappe.db.exists("Network Printer Settings", doc_name):
		frappe.delete_doc("Network Printer Settings", doc_name)

	doc = frappe.get_doc(
		{
			"doctype": "Network Printer Settings",
			"name": doc_name,
			"server_ip": "localhost",
			"port": 631,
			"printer_name": "ZD621",
			"printer_location": "Chelsea Receiving",
			"device_uri": "socket://192.168.1.50:9100",
		}
	).insert()

	mock_conn = mock_cups_connection(
		get_printers={
			"ZD621": {
				"printer-make-and-model": "Local Raw Printer",
				"printer-location": "Chelsea Receiving",
				"device-uri": "socket://192.168.1.50:9100",
			}
		}
	)
	reachable_uri = {
		"host": "192.168.1.55",
		"port": 9100,
		"ping_result": {"reachable": True, "host": "192.168.1.55", "message": "ok"},
		"socket_reachable": True,
		"message": "ok",
		"warnings": [],
	}
	with patch.object(nps, "cups_connection", return_value=mock_conn), patch.object(
		nps, "validate_device_uri", return_value=reachable_uri
	):
		updated = doc.configure_printer_queue(
			device_uri="socket://192.168.1.55:9100",
			ppdname="raw",
			printer_location="Chelsea Receiving Dock",
			enabled=1,
		)

	assert updated["device_uri"] == "socket://192.168.1.55:9100"
	assert updated["printer_location"] == "Chelsea Receiving Dock"
	mock_conn.setPrinterDevice.assert_called_once()


@pytest.mark.order(126)
def test_is_local_cups_server():
	assert nps.is_local_cups_server("localhost", 631) is True
	assert nps.is_local_cups_server("127.0.0.1", 631) is True
	assert nps.is_local_cups_server("10.1.10.1", 631) is False


@pytest.mark.order(128)
def test_parse_device_uri_host_extracts_socket_address():
	assert nps.parse_device_uri_host("socket://192.168.1.50:9100") == "192.168.1.50"
	assert nps.parse_device_uri_host("ipp://zebra.local/ipp/print") == "zebra.local"
	assert nps.parse_device_uri_host("") is None


@pytest.mark.order(130)
def test_ping_host_reports_local_print_server():
	result = nps.ping_host("localhost")
	assert result["reachable"] is True
	assert "local" in result["message"].lower()


@pytest.mark.order(156)
def test_get_cups_printer_info_returns_location_and_uri():
	doc_name = "Chelsea Receiving Labels Info"
	if frappe.db.exists("Network Printer Settings", doc_name):
		frappe.delete_doc("Network Printer Settings", doc_name)

	doc = frappe.get_doc(
		{
			"doctype": "Network Printer Settings",
			"name": doc_name,
			"server_ip": "localhost",
			"port": 631,
			"printer_name": "ZD621",
		}
	).insert()

	mock_conn = mock_cups_connection(
		get_printers={
			"ZD621": {
				"printer-make-and-model": "Zebra ZD621",
				"printer-location": "Chelsea Receiving Dock",
				"device-uri": "socket://192.168.1.50:9100",
			}
		}
	)
	with patch.object(nps, "cups_connection", return_value=mock_conn):
		info = doc.get_cups_printer_info()

	assert info["printer_location"] == "Chelsea Receiving Dock"
	assert info["device_uri"] == "socket://192.168.1.50:9100"


@pytest.mark.order(158)
def test_print_test_page_submits_cups_job():
	doc_name = "Chelsea Receiving Labels Test Page"
	if frappe.db.exists("Network Printer Settings", doc_name):
		frappe.delete_doc("Network Printer Settings", doc_name)

	doc = frappe.get_doc(
		{
			"doctype": "Network Printer Settings",
			"name": doc_name,
			"server_ip": "localhost",
			"port": 631,
			"printer_name": "ZD621",
		}
	).insert()

	mock_conn = mock_cups_connection(
		get_printers={
			"ZD621": {
				"printer-make-and-model": "Zebra ZD621",
				"device-uri": "socket://192.168.1.50:9100",
			}
		}
	)
	mock_conn.printTestPage = Mock(return_value=42)
	with patch.object(nps, "cups_connection", return_value=mock_conn):
		result = doc.print_test_page()

	mock_conn.printTestPage.assert_called_once_with("ZD621")
	assert result["job_id"] == 42


@pytest.mark.order(160)
def test_ping_printer_uses_device_uri_host():
	doc_name = "Chelsea Receiving Labels Ping"
	if frappe.db.exists("Network Printer Settings", doc_name):
		frappe.delete_doc("Network Printer Settings", doc_name)

	doc = frappe.get_doc(
		{
			"doctype": "Network Printer Settings",
			"name": doc_name,
			"server_ip": "localhost",
			"port": 631,
			"printer_name": "ZD621",
			"device_uri": "socket://192.168.1.50:9100",
		}
	).insert()

	mock_conn = mock_cups_connection(
		get_printers={
			"ZD621": {
				"printer-make-and-model": "Zebra ZD621",
				"printer-location": "Chelsea Receiving",
				"device-uri": "socket://192.168.1.50:9100",
			}
		}
	)
	with patch.object(nps, "cups_connection", return_value=mock_conn), patch.object(
		nps, "ping_host", return_value={"reachable": True, "host": "192.168.1.50", "message": "ok"}
	) as mock_ping:
		result = doc.ping_printer()

	mock_ping.assert_called_once_with("192.168.1.50")
	assert result["cups_location"] == "Chelsea Receiving"


@pytest.mark.order(162)
def test_delete_printer_queue_removes_cups_and_nps():
	"""Decommissioning removes ZD621 from CUPS and deletes the ERPNext record."""
	doc_name = "Chelsea Receiving Labels Delete"
	if frappe.db.exists("Network Printer Settings", doc_name):
		frappe.delete_doc("Network Printer Settings", doc_name)

	doc = frappe.get_doc(
		{
			"doctype": "Network Printer Settings",
			"name": doc_name,
			"server_ip": "localhost",
			"port": 631,
			"printer_name": "ZD621",
		}
	).insert()

	mock_conn = mock_cups_connection()
	with patch.object(nps, "cups_connection", return_value=mock_conn):
		doc.delete_printer_queue()

	mock_conn.deletePrinter.assert_called_once_with("ZD621")
	assert not frappe.db.exists("Network Printer Settings", doc_name)


@pytest.mark.order(164)
def test_push_location_to_cups_logs_sync_failure():
	"""Saving Chelsea Receiving Labels logs when CUPS rejects the location update."""
	doc_name = "Chelsea Receiving Labels Location Sync"
	if frappe.db.exists("Network Printer Settings", doc_name):
		frappe.delete_doc("Network Printer Settings", doc_name)

	doc = frappe.get_doc(
		{
			"doctype": "Network Printer Settings",
			"name": doc_name,
			"server_ip": "localhost",
			"port": 631,
			"printer_name": "ZD621",
			"printer_location": "Chelsea Receiving",
		}
	).insert()

	mock_conn = mock_cups_connection()
	mock_conn.setPrinterLocation.side_effect = RuntimeError("CUPS unavailable")
	with (
		patch.object(nps, "cups_connection", return_value=mock_conn),
		patch("frappe.log_error") as mock_log_error,
	):
		doc.printer_location = "Chelsea Receiving Dock"
		doc.save()

	mock_log_error.assert_called_once()
	assert "CUPS location sync failed" in mock_log_error.call_args.kwargs["title"]
	frappe.delete_doc("Network Printer Settings", doc_name)
