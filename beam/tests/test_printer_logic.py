# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import pytest

from beam.beam.overrides import network_printer_settings as nps


@pytest.mark.order(110)
def test_parse_device_uri_port_defaults_socket_to_9100():
	assert nps.parse_device_uri_port("socket://192.168.1.50:9100") == 9100
	assert nps.parse_device_uri_port("socket://192.168.1.50") == 9100


@pytest.mark.order(112)
def test_validate_device_uri_warns_on_port_63():
	result = nps.validate_device_uri("socket://192.168.1.50:63")
	assert any("9100" in warning for warning in result["warnings"])


@pytest.mark.order(114)
def test_map_printer_state_to_indicator_stopped():
	indicator = nps.map_printer_state_to_indicator(
		nps.PRINTER_STATE_STOPPED,
		"offline-report",
	)
	assert indicator["color"] == "red"
	assert indicator["label"] == "Offline"


@pytest.mark.order(116)
def test_map_printer_state_to_indicator_accepts_list_reasons():
	indicator = nps.map_printer_state_to_indicator(
		nps.PRINTER_STATE_STOPPED,
		["offline-report", "paused"],
	)
	assert indicator["color"] == "red"
	assert indicator["label"] == "Offline"


@pytest.mark.order(118)
def test_map_printer_state_to_indicator_processing():
	indicator = nps.map_printer_state_to_indicator(nps.PRINTER_STATE_PROCESSING)
	assert indicator["color"] == "blue"
	assert indicator["label"] == "Processing"


@pytest.mark.order(120)
def test_classify_fleet_row_orphan_queue():
	row = nps.classify_fleet_row(
		"vRAW",
		{
			"printer-location": "Chelsea Receiving",
			"device-uri": "socket://192.168.1.51:9100",
			"printer-state": nps.PRINTER_STATE_IDLE,
		},
	)
	assert row["status"] == "Orphan Queue"
	assert row["cups_queue"] == "vRAW"


@pytest.mark.order(122)
def test_classify_fleet_row_mismatch():
	row = nps.classify_fleet_row(
		"ZD621",
		{
			"printer-location": "Chelsea Receiving Dock",
			"device-uri": "socket://192.168.1.50:9100",
			"printer-state": nps.PRINTER_STATE_IDLE,
		},
		{
			"name": "Chelsea Receiving Labels",
			"printer_location": "Chelsea Receiving",
			"device_uri": "socket://192.168.1.55:9100",
		},
	)
	assert row["status"] == "Mismatch"


@pytest.mark.order(124)
def test_build_test_zpl_contains_queue_and_printer_name():
	zpl = nps.build_test_zpl("ZD621", "Chelsea Receiving Labels")
	assert "^XA" in zpl
	assert "ZD621" in zpl
	assert "Chelsea Receiving Labels" in zpl
