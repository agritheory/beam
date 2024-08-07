import pathlib
import sqlite3

import frappe
from frappe.utils import get_site_path
from frappe.utils.synchronization import filelock


def get_demand_db() -> sqlite3.Connection:
	path = pathlib.Path(f"{get_site_path()}/demand.db").resolve()
	with filelock(str(path)):
		with sqlite3.connect(path) as conn:
			cur = conn.cursor()
			cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='demand';")
			data = cur.fetchone()
			if data:
				return sqlite3.connect(path)

			# else setup table
			cur.execute(
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
			cur.execute(
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
			cur.execute("CREATE INDEX idx_demand_key ON demand(key)")
			cur.execute("CREATE INDEX idx_demand_company ON demand(company)")
			cur.execute("CREATE INDEX idx_demand_warehouse ON demand(warehouse)")
			cur.execute("CREATE INDEX idx_demand_item_code ON demand(item_code)")
			cur.execute("CREATE INDEX idx_demand_delivery_date ON demand(delivery_date)")

			cur.execute("CREATE INDEX idx_allocation_key ON allocation(key)")
			cur.execute("CREATE INDEX idx_allocation_demand ON allocation(demand)")
			cur.execute("CREATE INDEX idx_allocation_company ON allocation(company)")
			cur.execute("CREATE INDEX idx_allocation_warehouse ON allocation(warehouse)")
			cur.execute("CREATE INDEX idx_allocation_item_code ON allocation(item_code)")

			return sqlite3.connect(path)


def dict_factory(cursor: sqlite3.Cursor, row: dict) -> frappe._dict:
	d = frappe._dict({})
	for idx, col in enumerate(cursor.description):
		d[col[0]] = row[idx]
	return d
