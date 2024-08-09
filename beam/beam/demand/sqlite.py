import pathlib
import sqlite3

import frappe
from frappe.utils import get_site_path
from frappe.utils.synchronization import filelock


def get_demand_db_path() -> pathlib.Path:
	return pathlib.Path(f"{get_site_path()}/demand.db").resolve()


def get_demand_db() -> sqlite3.Connection:
	path = get_demand_db_path()
	with filelock(str(path)), sqlite3.connect(path) as conn:
		cursor = conn.cursor()
		cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='demand';")
		data = cursor.fetchone()
		if data:
			return sqlite3.connect(path)
		return create_demand_db(cursor)


def create_demand_db(cursor: sqlite3.Cursor) -> sqlite3.Connection:
	path = get_demand_db_path()
	cursor.execute(
		"""
			CREATE TABLE demand(
				key text,
				doctype text,
				company text,
				parent text,
				warehouse text,
				name text,
				item_code text,
				delivery_date int,
				modified int,
				total_required_qty real,
				stock_uom text,
				assigned text
			)
		"""
	)
	cursor.execute(
		"""
			CREATE TABLE allocation(
				key text,
				demand text,
				doctype text,
				company text,
				parent text,
				warehouse text,
				name text,
				item_code text,
				allocated_date int,
				modified int,
				allocated_qty real,
				stock_uom text,
				status text,
				assigned text
			)
		"""
	)
	cursor.execute("CREATE INDEX idx_demand_key ON demand(key)")
	cursor.execute("CREATE INDEX idx_demand_company ON demand(company)")
	cursor.execute("CREATE INDEX idx_demand_warehouse ON demand(warehouse)")
	cursor.execute("CREATE INDEX idx_demand_item_code ON demand(item_code)")
	cursor.execute("CREATE INDEX idx_demand_delivery_date ON demand(delivery_date)")

	cursor.execute("CREATE INDEX idx_allocation_key ON allocation(key)")
	cursor.execute("CREATE INDEX idx_allocation_demand ON allocation(demand)")
	cursor.execute("CREATE INDEX idx_allocation_company ON allocation(company)")
	cursor.execute("CREATE INDEX idx_allocation_warehouse ON allocation(warehouse)")
	cursor.execute("CREATE INDEX idx_allocation_item_code ON allocation(item_code)")

	return sqlite3.connect(path)


def dict_factory(cursor: sqlite3.Cursor, row: sqlite3.Row) -> frappe._dict:
	_dict = frappe._dict()
	for idx, col in enumerate(cursor.description):
		_dict[col[0]] = row[idx]
	return _dict