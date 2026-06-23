# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest
from test_utils.printers import ipp_printer_sync, raw_printer_sync

from beam.beam.overrides import network_printer_settings as nps
from beam.beam.report.printer_fleet_status.printer_fleet_status import execute
from cups_test_utils import (
	MOCK_PRINTER_BIND_HOST,
	cups_test_connection,
	delete_nps_if_exists,
	device_uri_for_cups,
	submit_ipp_print_job,
	temporary_cups_queue,
)


@pytest.mark.order(170)
def test_create_queue_prints_zpl_test_label_to_fake_printer(cups_server):
	"""Chelsea Receiving Labels sends a ZPL test label to the fake ZD621 raw printer."""
	nps_name = "Chelsea Receiving Labels Integration"
	queue_name = "BEAM_TEST_ZD621"
	delete_nps_if_exists(nps_name)

	with raw_printer_sync(host=MOCK_PRINTER_BIND_HOST) as printer:
		device_uri = device_uri_for_cups(printer, cups_server)
		with temporary_cups_queue(queue_name, device_uri, cups_server) as conn:
			assert queue_name in conn.getPrinters()
			doc = frappe.get_doc(
				{
					"doctype": "Network Printer Settings",
					"name": nps_name,
					"server_ip": cups_server["host"],
					"port": cups_server["port"],
					"printer_name": queue_name,
					"printer_type": "Label / RAW",
					"device_uri": device_uri,
				}
			).insert()

			result = doc.print_test_page()
			assert result["test_type"] == "zpl"
			payload = printer.wait_for_payload()
			text = payload.decode("utf-8", errors="replace")
			assert "^XA" in text
			assert queue_name in text

		delete_nps_if_exists(nps_name)


@pytest.mark.order(172)
def test_configure_printer_updates_device_uri_on_cups(cups_server):
	"""Administrator retargets Chelsea Receiving Labels to a new fake printer URI."""
	nps_name = "Chelsea Receiving Labels Configure Integration"
	queue_name = "BEAM_TEST_CONFIGURE"
	delete_nps_if_exists(nps_name)

	with (
		raw_printer_sync(host=MOCK_PRINTER_BIND_HOST) as first_printer,
		raw_printer_sync(host=MOCK_PRINTER_BIND_HOST) as second_printer,
	):
		first_device_uri = device_uri_for_cups(first_printer, cups_server)
		second_device_uri = device_uri_for_cups(second_printer, cups_server)
		with temporary_cups_queue(queue_name, first_device_uri, cups_server):
			doc = frappe.get_doc(
				{
					"doctype": "Network Printer Settings",
					"name": nps_name,
					"server_ip": cups_server["host"],
					"port": cups_server["port"],
					"printer_name": queue_name,
					"printer_type": "Label / RAW",
					"device_uri": first_device_uri,
				}
			).insert()

			updated = doc.configure_printer_queue(device_uri=second_device_uri, accept_jobs=1)
			assert updated["device_uri"] == second_device_uri

			conn = cups_test_connection(cups_server)
			cups_uri = conn.getPrinters()[queue_name]["device-uri"]
			assert cups_uri == second_device_uri

		delete_nps_if_exists(nps_name)


@pytest.mark.order(174)
def test_configure_printer_reject_jobs(cups_server):
	"""Chelsea dock ZD621 stops accepting jobs without deleting the queue."""
	nps_name = "Chelsea Receiving Labels Reject Integration"
	queue_name = "BEAM_TEST_REJECT"
	delete_nps_if_exists(nps_name)

	with raw_printer_sync(host=MOCK_PRINTER_BIND_HOST) as printer:
		device_uri = device_uri_for_cups(printer, cups_server)
		with temporary_cups_queue(queue_name, device_uri, cups_server):
			doc = frappe.get_doc(
				{
					"doctype": "Network Printer Settings",
					"name": nps_name,
					"server_ip": cups_server["host"],
					"port": cups_server["port"],
					"printer_name": queue_name,
					"printer_type": "Label / RAW",
					"device_uri": device_uri,
				}
			).insert()

			doc.configure_printer_queue(accept_jobs=0)
			status = doc.get_cups_printer_status()
			assert status["is_accepting_jobs"] is False

		delete_nps_if_exists(nps_name)


@pytest.mark.order(176)
def test_fleet_report_lists_orphan_vraw_queue(cups_server):
	"""Legacy vRAW on CUPS appears as an orphan queue in the fleet report."""
	queue_name = "BEAM_TEST_ORPHAN_VRAW"
	probe_name = "Chelsea Print Server Fleet Probe"
	delete_nps_if_exists(probe_name)

	frappe.get_doc(
		{
			"doctype": "Network Printer Settings",
			"name": probe_name,
			"server_ip": cups_server["host"],
			"port": cups_server["port"],
			"printer_name": "BEAM_TEST_PROBE",
			"printer_type": "Label / RAW",
		}
	).insert()

	with raw_printer_sync(host=MOCK_PRINTER_BIND_HOST) as printer:
		device_uri = device_uri_for_cups(printer, cups_server)
		with temporary_cups_queue(queue_name, device_uri, cups_server):
			columns, rows = execute({"server_ip": cups_server["host"]})
			orphan_rows = [row for row in rows if row.get("cups_queue") == queue_name]
			assert orphan_rows
			assert orphan_rows[0]["status"] == "Orphan Queue"

	delete_nps_if_exists(probe_name)


@pytest.mark.order(178)
def test_create_queue_fails_when_device_unreachable(cups_server):
	"""Stock Manager cannot create Chelsea Receiving Labels against a dead socket URI."""
	nps_name = "Chelsea Receiving Labels Dead Socket"
	queue_name = "BEAM_TEST_DEAD"
	delete_nps_if_exists(nps_name)
	existing = set(frappe.get_all("Network Printer Settings", pluck="name"))

	with pytest.raises(frappe.ValidationError):
		nps.create_printer_queue(
			nps_name,
			cups_server["host"],
			cups_server["port"],
			queue_name,
			"socket://127.0.0.1:1",
			ppdname="raw",
			printer_location="Chelsea Receiving",
			printer_type="Label / RAW",
		)

	created = set(frappe.get_all("Network Printer Settings", pluck="name")) - existing
	assert nps_name not in created
	conn = cups_test_connection(cups_server)
	assert queue_name not in conn.getPrinters()


@pytest.mark.order(179)
def test_create_queue_registers_ipp_device_and_delivers_print_job(cups_server, tmp_path):
	"""Office PDF queue registers mock IPP on CUPS; Print-Job at that URI lands in save_dir."""
	nps_name = "Office PDF Mock IPP Integration"
	queue_name = "BEAM_TEST_IPP"
	delete_nps_if_exists(nps_name)

	with ipp_printer_sync(save_dir=tmp_path, name="PDF", host=MOCK_PRINTER_BIND_HOST) as printer:
		device_uri = device_uri_for_cups(printer, cups_server)
		# Mock IPP does not satisfy IPP Everywhere probes; raw PPD still registers the ipp:// device URI.
		with temporary_cups_queue(queue_name, device_uri, cups_server, ppdname="raw") as conn:
			assert conn.getPrinters()[queue_name]["device-uri"] == device_uri

			doc = frappe.get_doc(
				{
					"doctype": "Network Printer Settings",
					"name": nps_name,
					"server_ip": cups_server["host"],
					"port": cups_server["port"],
					"printer_name": queue_name,
					"printer_type": "General Purpose",
					"device_uri": device_uri,
				}
			).insert()

			result = doc.print_test_page()
			assert result["test_type"] in ("testpage", "text")
			assert result["job_id"]

			submit_ipp_print_job(
				printer,
				b"Office PDF integration test\n",
				job_name=queue_name,
			)
			assert printer.job_count >= 1
			assert list(tmp_path.glob("job_*"))

		delete_nps_if_exists(nps_name)
