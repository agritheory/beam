# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

from datetime import datetime


def parse_frappe_datetime(value: str) -> float:
	"""Same normalization as beam/www/beam/utils/parseFrappeDatetime.ts."""
	if not value:
		return float("nan")
	normalized = value.replace(" ", "T", 1)
	dot = normalized.find(".")
	if dot != -1:
		normalized = normalized[: dot + 4]
	return datetime.fromisoformat(normalized).timestamp() * 1000


def test_frappe_datetime_with_microseconds_parses():
	ms = parse_frappe_datetime("2026-10-10 14:00:00.123456")
	assert ms == parse_frappe_datetime("2026-10-10 14:00:00.123")
