# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

from contextlib import contextmanager

import frappe

from beam.beam.overrides.network_printer_settings import (
	cups_connection,
	default_ppd_for_type,
	require_cups,
	run_cups_admin,
)


def cups_available(server_ip="localhost", port=631):
	try:
		require_cups()
		conn = cups_connection(server_ip, port)
		conn.getPrinters()
	except Exception:
		return False
	return True


def require_local_cups(server_ip="localhost", port=631):
	if not cups_available(server_ip, port):
		raise RuntimeError(
			"Local CUPS is required for integration tests (localhost:631, bench user in lpadmin)."
		)


@contextmanager
def temporary_cups_queue(queue_name, device_uri, server_ip="localhost", port=631, ppdname=None):
	require_local_cups(server_ip, port)
	conn = cups_connection(server_ip, port)
	ppdname = ppdname or default_ppd_for_type("Label / RAW")

	def create_queue():
		if queue_name in conn.getPrinters():
			conn.deletePrinter(queue_name)
		conn.addPrinter(queue_name, ppdname=ppdname, device=device_uri, info=queue_name, location="")
		conn.enablePrinter(queue_name)
		conn.acceptJobs(queue_name)

	def delete_queue():
		if queue_name in conn.getPrinters():
			conn.deletePrinter(queue_name)

	run_cups_admin("create test queue", create_queue)
	try:
		yield conn
	finally:
		run_cups_admin("delete test queue", delete_queue)


def delete_nps_if_exists(name):
	if frappe.db.exists("Network Printer Settings", name):
		frappe.delete_doc("Network Printer Settings", name)
