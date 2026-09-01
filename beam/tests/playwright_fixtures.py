# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt
#
# Playwright fixtures for BEAM portal tests (test_beam_*.py).
# Load from those modules via: pytest_plugins = ["beam.tests.playwright_fixtures"]
#
# IMPORTANT: pytest_plugins registers this module session-wide once any
# test_beam_* file is collected. Autouse fixtures MUST gate on test_beam_*
# or they delete draft Purchase Receipts / enable real commits during the
# unit story (MagicMock commit + fixture PRs), which breaks handling-unit tests.
#
# Root conftest mocks frappe.db.commit for the unit story; use_real_database_commits
# swaps in real commits (module scope) so bench serve sees pytest-side setup.
# test_beam_* files use @pytest.mark.order(300+) so they run after the unit story.

from pathlib import Path
from unittest.mock import MagicMock

import frappe
import pytest
from frappe.database.mariadb.database import MariaDBDatabase

from beam.beam.demand.demand import build_demand_allocation_map
from beam.beam.demand.receiving import reset_build_receiving_map
from beam.tests.playwright_utils import (
	ensure_bench_web_running,
	get_playwright_base_url,
	init_playwright_url_state,
	login_playwright,
)


def is_beam_portal_test(request) -> bool:
	path = getattr(request, "fspath", None) or getattr(request, "path", None)
	if path is None and hasattr(request, "node"):
		path = getattr(request.node, "fspath", None) or getattr(request.node, "path", None)
	return Path(str(path)).name.startswith("test_beam_") if path else False


def rebuild_demand_databases():
	"""Rebuild every demand.db table from MariaDB.

	Two calls because demand/allocation and receiving are rebuilt by separate
	entry points; they are independent, so the order does not matter.
	"""
	build_demand_allocation_map()
	reset_build_receiving_map()


@pytest.fixture(scope="session")
def playwright_bench_web():
	ensure_bench_web_running()


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args, request, playwright_bench_web):
	# emulate an Android barcode scanner
	args = {
		**browser_context_args,
		"viewport": {
			"width": 400,
			"height": 900,
		},
	}
	base_url = getattr(request.config.option, "base_url", None)
	init_playwright_url_state(base_url=base_url)
	return args


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args, request, playwright_bench_web):
	base_url = getattr(request.config.option, "base_url", None)
	env = init_playwright_url_state(base_url=base_url)
	map_host = env.get("playwright_resolver_map_host")
	if not map_host:
		return browser_type_launch_args
	launch_args = list(browser_type_launch_args.get("args") or [])
	launch_args.append(f"--host-resolver-rules=MAP {map_host} 127.0.0.1")
	return {**browser_type_launch_args, "args": launch_args}


@pytest.fixture(scope="module", autouse=True)
def use_real_database_commits(request):
	"""Real commits for portal modules so bench serve sees pytest-side seeding."""
	if not is_beam_portal_test(request):
		yield frappe.db
		return

	# Nothing the unit story wrote has been committed — its commit was a MagicMock,
	# so all of it is still open on this connection. Turning on real commits would
	# flush that backlog into the site for good on the first portal write, leaving
	# documents like `Pie Servingware` behind and breaking the next run's asserts.
	# Discard it first; the fixtures from before_test were committed out-of-band
	# and survive. clear_cache drops redis copies of the rolled-back docs, which
	# bench serve would otherwise still serve.
	if isinstance(frappe.db.commit, MagicMock):
		frappe.db.rollback()
		frappe.clear_cache()
		frappe.db.commit = lambda: MariaDBDatabase.commit(frappe.db)

	# Hooks wrote to demand.db outside that rollback, so it still describes
	# documents MariaDB no longer has. Rebuild from what MariaDB holds now.
	rebuild_demand_databases()

	yield frappe.db

	# Real portal commits mutate stock/orders and demand hooks; resync maps after
	# each portal module so the next module (and session teardown) see truth.
	rebuild_demand_databases()


@pytest.fixture(autouse=True)
def setup(request):
	if not is_beam_portal_test(request):
		yield
		return

	# Only resolve Playwright's page fixture for portal tests.
	page = request.getfixturevalue("page")
	delete_draft_records(["Purchase Receipt", "Stock Entry", "Delivery Note"])

	page.set_default_timeout(5000)

	base_url = get_playwright_base_url()

	# Skip auto-login for scan-to-login tests (they need to start from login page)
	is_login_test = "scan_to_login" in request.node.name

	if not is_login_test:
		page.goto(base_url)
		# visiting the home page redirects to login page
		login_playwright(page)

	yield
	# Do not cancel submitted Purchase Receipts here. Portal tests commit for real;
	# later Stock Entries (transfer/repack/ship) consume that stock, so cancel hits
	# NegativeStockError and surfaces as ERROR at teardown. Draft cleanup is enough
	# (delete_draft_records at the start of each portal test).


def delete_draft_records(doctypes: list[str]):
	for doctype in doctypes:
		records = frappe.get_all(doctype, filters={"docstatus": 0}, pluck="name")
		for record in records:
			frappe.delete_doc(doctype, record, force=True)
