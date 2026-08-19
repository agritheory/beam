# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import os
import time
from contextlib import contextmanager
from urllib.parse import urlparse, urlunparse

import frappe
import httpx
from test_utils.printers.ipp.codec import IppEncoder, IppOperation, IppTag

from beam.beam.overrides.network_printer_settings import (
	default_ppd_for_type,
	require_cups,
	run_cups_admin,
)

CUPS_HOST_FROM_CONTAINER = "host.docker.internal"
# Mock printers must listen on all interfaces so a CUPS *container* can reach them
# via host.docker.internal / host-gateway (127.0.0.1-only listeners reject those connections).
# Same-host system cupsd uses 127.0.0.1 in the device URI instead (see mock_host_for_cups).
MOCK_PRINTER_BIND_HOST = "0.0.0.0"

LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1", "0.0.0.0"})


def cups_runs_on_same_host(host: str, port: int) -> bool:
	"""True when CUPS is system cupsd on this machine (not a published container port).

	CI publishes beam-cups as 127.0.0.1:1631 — still a container that must reach mocks
	via host-gateway. Default local cupsd is :631 on the same host as the mock printers.
	"""
	flag = os.environ.get("BEAM_CUPS_SAME_HOST", "").strip().lower()
	if flag in ("1", "true", "yes"):
		return True
	if flag in ("0", "false", "no"):
		return False
	return host in LOOPBACK_HOSTS and int(port) == 631


def mock_host_for_cups(host: str = "127.0.0.1", port: int = 631) -> str:
	"""Hostname CUPS should use in device URIs to reach mock printers in the test process.

	- Same-host system cupsd: 127.0.0.1 (no Docker; host.docker.internal would hang).
	- CI / container CUPS: runner IP or host.docker.internal.
	- Override anytime with BEAM_CUPS_MOCK_HOST.
	"""
	explicit = os.environ.get("BEAM_CUPS_MOCK_HOST", "").strip()
	if explicit:
		return explicit
	if cups_runs_on_same_host(host, port):
		return "127.0.0.1"
	if os.environ.get("CI") == "true" or os.environ.get("ACT") == "true":
		import subprocess

		try:
			ip = subprocess.check_output(["hostname", "-I"], text=True).split()[0]
			if ip:
				return ip
		except (IndexError, subprocess.CalledProcessError, FileNotFoundError):
			pass
	return CUPS_HOST_FROM_CONTAINER


def mock_host_for_cups_container():
	"""Backward-compatible alias; uses BEAM_CUPS_HOST/PORT when set."""
	host = os.environ.get("BEAM_CUPS_HOST", "127.0.0.1")
	port = int(os.environ.get("BEAM_CUPS_PORT", "631"))
	return mock_host_for_cups(host, port)


def cups_test_connection(server):
	"""Admin connection to the CUPS under test.

	Same-host system cupsd must use the Unix socket — HTTP to 127.0.0.1:631
	accepts getPrinters but hangs forever on addPrinter/deletePrinter (matches
	beam.beam.overrides.network_printer_settings.cups_connection).
	"""
	cups = require_cups()
	password = server["password"]
	cups.setUser(server["user"])
	cups.setPasswordCB(lambda prompt: password)

	host = (server.get("host") or "").strip()
	port = int(server.get("port") or 631)
	same_host = server.get("same_host")
	if same_host is None:
		same_host = cups_runs_on_same_host(host, port)

	if same_host or (port == 631 and host.lower() in LOOPBACK_HOSTS):
		cups.setServer("")
		cups.setPort(631)
		return cups.Connection()

	cups.setServer(host)
	cups.setPort(port)
	return cups.Connection()


def cups_available(server):
	try:
		conn = cups_test_connection(server)
		conn.getPrinters()
	except Exception:
		return False
	return True


def device_uri_for_cups(printer, server):
	uri = printer.uri
	replacement_host = server.get("cups_host_from_container") or mock_host_for_cups(
		server.get("host", "127.0.0.1"), int(server.get("port", 631))
	)
	parsed = urlparse(uri)
	if parsed.hostname not in LOOPBACK_HOSTS:
		return uri

	hostname = replacement_host
	if parsed.hostname == "::1" and replacement_host not in LOOPBACK_HOSTS:
		hostname = f"[{replacement_host}]"

	netloc = hostname
	if parsed.port:
		netloc = f"{hostname}:{parsed.port}"
	if parsed.username:
		userinfo = parsed.username
		if parsed.password:
			userinfo = f"{userinfo}:{parsed.password}"
		netloc = f"{userinfo}@{netloc}"

	return urlunparse(parsed._replace(netloc=netloc))


@contextmanager
def temporary_cups_queue(queue_name, device_uri, server, ppdname=None):
	conn = cups_test_connection(server)
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


def submit_ipp_print_job(printer, document: bytes, job_name: str, mime_type: str = "text/plain"):
	"""Send a Print-Job to the mock IPP server at the printer's registered URI."""
	enc = IppEncoder()
	enc.write_header((1, 1), IppOperation.PRINT_JOB, 1)
	enc.write_tag(IppTag.OPERATION)
	enc.write_charset("attributes-charset", "utf-8")
	enc.write_language("attributes-natural-language", "en")
	enc.write_uri("printer-uri", printer.uri)
	enc.write_name("job-name", job_name)
	enc.write_mime_type("document-format", mime_type)
	enc.write_tag(IppTag.END)
	response = httpx.post(
		f"http://{printer.address}{printer.printer_path}",
		content=enc.get_bytes() + document,
		headers={"Content-Type": "application/ipp"},
		timeout=5.0,
	)
	response.raise_for_status()
	return response


def configure_pycups_credentials(server):
	cups = require_cups()
	password = server["password"]
	cups.setUser(server["user"])
	cups.setPasswordCB(lambda prompt: password)


def wait_for_cups_http(server, timeout=120.0):
	url = f"http://{server['host']}:{server['port']}/"
	auth = (server["user"], server["password"])
	with httpx.Client(timeout=5.0) as client:
		for _ in range(int(timeout / 2)):
			try:
				response = client.get(url, auth=auth)
				if response.status_code < 500:
					return
			except httpx.HTTPError:
				pass
			time.sleep(2)
	raise RuntimeError(f"CUPS did not become ready at {url} within {timeout}s")
