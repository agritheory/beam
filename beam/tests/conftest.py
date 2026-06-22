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
# 170–178 | Live CUPS — ZD621 at Chelsea dock (requires local CUPS + lpadmin)
# 180–200 | Print queue panel — job snapshots, client polling, permissions

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import frappe
import pytest
from frappe.utils import get_bench_path

TESTS_DIR = Path(__file__).resolve().parent
if str(TESTS_DIR) not in sys.path:
	sys.path.insert(0, str(TESTS_DIR))


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
