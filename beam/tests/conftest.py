# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

# Business story (Ambrosia Pie Company)
#
# Order | Chapter
# ------|---------
# 10 | BEAM Settings — handling units enabled
# 20–28 | Barcodes — Code128 generation, labels, print format
# 40–48 | Scanning — list/form scan actions, delivery note hooks
# 60–70 | Receiving & production — purchase receipt through manufacture
# 71 | Serialized finished goods — serial number scan
# 72–92 | Outbound & corrections — delivery, invoice, transfer, cancel paths
# 100–106 | Document printing — print_by_server format routing
# 110–132 | Print server logic — URI, CUPS state, fleet rows, ZPL, notifications
# 140–162 | Printer setup — wizard, configure, test print, decommission
# 166–168 | Printer setup — wizard API permissions
# 170–179 | Live CUPS — ZD621 at Chelsea dock (Docker + published CUPS container)
# 180–200 | Print queue panel — job snapshots, client polling, permissions
#
# Manual testing helpers
# ----------------------
# Prerequisites (local print server):
#   sudo apt-get install -y gcc cups python3-dev libcups2-dev printer-driver-cups-pdf
#   bench pip install pycups
#   sudo usermod -aG lpadmin $USER    # re-login or newgrp lpadmin
#   Use Server IP "localhost" (not 127.0.0.1) in Network Printer Settings — BEAM uses the
#   Unix socket and avoids CUPS HTTP auth errors.
#
# General Purpose / PDF testing (no physical printer):
#   sudo apt-get install -y printer-driver-cups-pdf
#   lpadmin -p PDF -E -v cups-pdf:/ -m everywhere -L "Office PDF"
#   cupsenable PDF && cupsaccept PDF
#   PDF output lands under /var/spool/cups-pdf/<username>/ (Debian/Ubuntu).
#   In ERPNext: wizard or Network Printer Settings with Printer Type "General Purpose",
#   queue name PDF, PPD "everywhere". Use Print Test or print_by_server from a document.
#
# Label / RAW testing without hardware (mock-printer CLI or sync wrapper):
#   pip install "git+https://github.com/agritheory/test_utils.git@v1.28.0"
#   mock-printer raw --save-dir /tmp/prints
#   mock-printer ipp --save-dir /tmp/prints
#   mock-printer both --save-dir /tmp/prints
#
#   from test_utils.printers import raw_printer_sync, ipp_printer_sync
#   from beam.tests.cups_test_utils import temporary_cups_queue, delete_nps_if_exists
#   with raw_printer_sync(save_dir="/tmp/prints") as printer:
#       print(printer.uri)    # e.g. socket://127.0.0.1:54321
#       with temporary_cups_queue("BEAM_TEST_ZD621", printer.uri):
#           ... create Network Printer Settings, print_test_page(), etc.
#           print(printer.last_text())   # captured ZPL payload
#
# Quick checks from bench console:
#   bench --site pinyon console
#   >>> from beam.beam.overrides import network_printer_settings as nps
#   >>> nps.cups_connection("localhost", 631).getPrinters()
#   >>> nps.get_wizard_devices("localhost", 631)
#   >>> from beam.beam import printer_queue as pq
#   >>> pq.get_printer_jobs_snapshot()
#
# Desk UI:
#   /app/printer-queue          — live job panel (polls every 4s, no background worker)
#   /app/query-report/Printer Fleet Status
#   http://localhost:631        — CUPS admin (remote admin needs extra cupsd.conf rules)
#
# Automated tests (pytest from bench root):
#   pytest apps/beam/beam/tests/test_printer_logic.py -v          # no CUPS required
#   pytest apps/beam/beam/tests/test_printer_wizard.py -v       # mocked CUPS
#   pytest apps/beam/beam/tests/test_printer_queue.py -v         # mocked CUPS
#   pytest apps/beam/beam/tests/test_printer_cups_integration.py -v   # Docker + CUPS container
#   bench --site pinyon set-config allow_tests true             # if bench run-tests is used

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import frappe
import pytest
from frappe.utils import get_bench_path
from testcontainers.core.container import DockerContainer
from testcontainers.core.image import DockerImage

from cups_test_utils import (
	CUPS_HOST_FROM_CONTAINER,
	configure_pycups_credentials,
	wait_for_cups_http,
)

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
	sys.path.insert(0, str(TESTS_DIR))

CUPS_CONTAINER_CONTEXT = TESTS_DIR.parents[1] / "cups" / "cups"
DEFAULT_CUPS_ADMIN_USER = os.environ.get("CUPS_ADMIN_USER", "admin")
DEFAULT_CUPS_ADMIN_PASSWORD = os.environ.get("CUPS_ADMIN_PASSWORD", "root")


def _get_logger(*args, **kwargs):
	from frappe.utils.logger import get_logger

	return get_logger(
		module=None,
		with_more_info=False,
		allow_site=True,
		filter=None,
		max_size=100_000,
		file_count=20,
		stream_only=True,
	)


@pytest.fixture(scope="module")
def monkeymodule():
	with pytest.MonkeyPatch.context() as mp:
		yield mp


@pytest.fixture(scope="session", autouse=True)
def db_instance():
	frappe.logger = _get_logger

	currentsite = "test_site"
	sites = Path(get_bench_path()) / "sites"
	if (sites / "common_site_config.json").is_file():
		currentsite = json.loads((sites / "common_site_config.json").read_text()).get("default_site")

	frappe.init(site=currentsite, sites_path=sites)
	frappe.connect()
	frappe.db.commit = MagicMock()
	yield frappe.db


def start_cups_container(image_ref):
	container = (
		DockerContainer(image_ref)
		.with_exposed_ports(631)
		.with_kwargs(extra_hosts={"host.docker.internal": "host-gateway"})
	)
	container.start()
	return container


@pytest.fixture(scope="module")
def cups_server():
	"""Start a CUPS container for the test module and tear it down immediately afterward.

	Scoped to module (not session) so the container is stopped as soon as
	test_printer_cups_integration.py finishes.  This avoids the Ryuk reconnection
	timeout that fires when the container outlives the test module in CI environments
	where TESTCONTAINERS_RYUK_DISABLED is not set.
	"""
	image_ref = os.environ.get("BEAM_CUPS_IMAGE")
	buildargs = {
		"CUPS_ADMIN_USER": DEFAULT_CUPS_ADMIN_USER,
		"CUPS_ADMIN_PASSWORD": DEFAULT_CUPS_ADMIN_PASSWORD,
	}
	server = {
		"user": DEFAULT_CUPS_ADMIN_USER,
		"password": DEFAULT_CUPS_ADMIN_PASSWORD,
		"cups_host_from_container": CUPS_HOST_FROM_CONTAINER,
	}

	try:
		if image_ref:
			container = start_cups_container(image_ref)
			try:
				server["host"] = container.get_container_host_ip()
				server["port"] = int(container.get_exposed_port(631))
				wait_for_cups_http(server)
				configure_pycups_credentials(server)
				yield server
			finally:
				container.stop()
		else:
			docker_image = DockerImage(
				path=CUPS_CONTAINER_CONTEXT,
				dockerfile_path="Containerfile",
				tag="beam-cups-test:local",
			)
			try:
				docker_image.build(buildargs=buildargs)
				container = start_cups_container(str(docker_image))
				try:
					server["host"] = container.get_container_host_ip()
					server["port"] = int(container.get_exposed_port(631))
					wait_for_cups_http(server)
					configure_pycups_credentials(server)
					yield server
				finally:
					container.stop()
			finally:
				docker_image.remove()
	except Exception as exc:
		raise RuntimeError(
			"CUPS integration tests require Docker. Start Docker, or set BEAM_CUPS_IMAGE "
			"to a pre-built image such as ghcr.io/agritheory/beam-cups:latest. "
			f"Original error: {exc}"
		) from exc
