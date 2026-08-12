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
# 170–200 | Print queue panel — job snapshots, client polling, permissions
# 210–220 | Live CUPS — ZD621 at Chelsea dock (workflow CUPS service container)
# 300–354 | BEAM portal (Playwright) — manufacture, receive, repack, login, ship, camera
#
# Manual testing helpers
# ----------------------
# Re-runs: MariaDB is transactional (frappe.db.commit is mocked), but demand.db
# is plain SQLite that hooks write to unconditionally, so it drifts out of sync
# every run. db_instance rebuilds it from MariaDB in a finally block at session
# teardown, and portal modules rebuild again on entry, so no manual step.
#
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
# Automated tests (pytest from apps/beam, bench env active):
#   pytest beam/tests --browser chromium
#     One suite: unit story (orders 10–220) then portal/Playwright (test_beam_*, 300+).
#     Requires: python -m playwright install chromium (once). Bench serve auto-starts.
#   pytest beam/tests --ignore-glob='**/test_beam_*.py'   # unit only
#   pytest beam/tests/test_printer_logic.py -v            # no CUPS required
#   pytest beam/tests/test_printer_cups_integration.py -v
#     Local (no Docker): system cupsd on :631, user in lpadmin. Admin calls use the
#     Unix socket (HTTP to 127.0.0.1:631 hangs on addPrinter). Device URIs stay on
#     127.0.0.1. CI: BEAM_CUPS_HOST/PORT → beam-cups container (port 1631).
#     Force same-host / container mock routing: BEAM_CUPS_SAME_HOST=1|0,
#     BEAM_CUPS_MOCK_HOST=<ip>.
#   bench --site pinyon set-config allow_tests true       # if bench run-tests is used

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import frappe
import pytest
from frappe.utils import get_bench_path

from beam.beam.demand.demand import build_demand_allocation_map
from beam.beam.demand.receiving import reset_build_receiving_map
from cups_test_utils import (
	configure_pycups_credentials,
	cups_runs_on_same_host,
	mock_host_for_cups,
	wait_for_cups_http,
)
from test_telemetry import emit as telemetry

TESTS_DIR = Path(__file__).resolve().parent

if str(TESTS_DIR) not in sys.path:
	sys.path.insert(0, str(TESTS_DIR))

DEFAULT_CUPS_ADMIN_USER = os.environ.get("CUPS_ADMIN_USER", "admin")
DEFAULT_CUPS_ADMIN_PASSWORD = os.environ.get("CUPS_ADMIN_PASSWORD", "root")


def rebuild_demand_databases():
	"""Rebuild demand.db (demand, allocation, receiving) from MariaDB.

	MariaDB stays clean on its own because frappe.db.commit is mocked, but
	SQLite has no transaction tied to it: every on_submit hook writes to
	demand.db and those rows survive the rollback. Rebuilding from MariaDB is
	the only thing that clears that drift.

	Two calls because demand/allocation and receiving are rebuilt by separate
	entry points; they are independent, so the order does not matter.
	"""
	build_demand_allocation_map()
	reset_build_receiving_map()


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

	frappe.init(site=currentsite, sites_path=sites, force=True)
	frappe.connect()
	# Unit tests stay transactional; portal modules (playwright_fixtures) swap in real commits.
	frappe.db.commit = MagicMock()

	rebuild_demand_databases()
	try:
		yield frappe.db
	finally:
		# finally, not a plain post-yield teardown: an interrupted or erroring
		# session would otherwise leave demand.db holding rows for documents
		# MariaDB rolled back, and the next run would read them as real.
		rebuild_demand_databases()


@pytest.fixture(scope="module")
def cups_server():
	"""Connect to local system cupsd or the CI beam-cups service.

	Defaults: 127.0.0.1:631 (same-host system CUPS). Device URIs keep loopback
	so cupsd can reach mock printers without host.docker.internal.

	CI sets BEAM_CUPS_PORT=1631 for the beam-cups container; mocks then use the
	runner IP / host.docker.internal. Override mock reachability with BEAM_CUPS_MOCK_HOST
	or force same-host mode with BEAM_CUPS_SAME_HOST=1.
	"""
	host = os.environ.get("BEAM_CUPS_HOST", "127.0.0.1")
	port = int(os.environ.get("BEAM_CUPS_PORT", "631"))
	mock_host = mock_host_for_cups(host, port)
	server = {
		"host": host,
		"port": port,
		"user": DEFAULT_CUPS_ADMIN_USER,
		"password": DEFAULT_CUPS_ADMIN_PASSWORD,
		"cups_host_from_container": mock_host,
		"same_host": cups_runs_on_same_host(host, port),
	}

	telemetry(
		f"cups_server connect host={host} port={port} "
		f"mock_host={mock_host} same_host={server['same_host']}"
	)
	try:
		wait_for_cups_http(server)
		configure_pycups_credentials(server)
	except Exception as exc:
		telemetry(f"cups_server failed: {exc}")
		raise RuntimeError(
			"CUPS integration tests require cupsd on "
			f"{host}:{port}. Locally: system cups on :631 (user in lpadmin). "
			"CI: beam-cups service with BEAM_CUPS_HOST/PORT. "
			f"Original error: {exc}"
		) from exc

	telemetry("cups_server ready")
	yield server
	telemetry("cups_server module complete")
