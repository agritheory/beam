import calendar
import pathlib
import sqlite3
from typing import TYPE_CHECKING

import frappe
from erpnext.stock.stock_balance import get_balance_qty_from_sle
from frappe.utils import get_site_path
from frappe.utils.data import get_datetime

if TYPE_CHECKING:
	from frappe.model.document import Document


def build_demand_map() -> None:
	transfer_demand = frappe.db.sql(
		"""
			SELECT
				'Work Order' AS doctype,
				`tabWork Order`.name AS parent,
				`tabWork Order`.wip_warehouse AS warehouse,
				`tabWork Order Item`.name,
				`tabWork Order Item`.item_code,
				`tabWork Order`.planned_start_date AS delivery_date,
				(`tabWork Order Item`.required_qty - `tabWork Order Item`.transferred_qty) AS net_required_qty
			FROM `tabWork Order`, `tabWork Order Item`
			WHERE
				`tabWork Order`.name = `tabWork Order Item`.parent
				AND (`tabWork Order Item`.transferred_qty - `tabWork Order Item`.required_qty) < 0
				AND `tabWork Order`.status = 'Not Started'
			ORDER BY `tabWork Order`.planned_start_date
		""",
		as_dict=True,
	)

	default_fg_warehouse = frappe.db.get_single_value(
		"Manufacturing Settings", "default_fg_warehouse"
	)
	sales_demand = frappe.db.sql(
		"""
			SELECT
				'Sales Order' AS doctype,
				`tabSales Order`.name AS parent,
				%(default_fg_warehouse)s AS warehouse,
				`tabSales Order Item`.name,
				`tabSales Order Item`.item_code,
				`tabSales Order`.delivery_date,
				(`tabSales Order Item`.stock_qty - `tabSales Order Item`.delivered_qty) AS net_required_qty
			FROM `tabSales Order`, `tabSales Order Item`
			WHERE
				`tabSales Order`.name = `tabSales Order Item`.parent
				AND `tabSales Order`.docstatus = 1
				AND `tabSales Order`.status != 'Closed'
				AND (`tabSales Order Item`.stock_qty - `tabSales Order Item`.delivered_qty) > 0
			ORDER BY `tabSales Order`.delivery_date
		""",
		{"default_fg_warehouse": default_fg_warehouse},
		as_dict=True,
	)
	for row in transfer_demand + sales_demand:
		row.key = frappe.generate_hash()
		row.delivery_date = str(calendar.timegm(get_datetime(row.delivery_date).timetuple()))
		row.net_required_qty = str(row.net_required_qty)
		row.actual_qty = str(get_balance_qty_from_sle(row.item_code, row.warehouse))

	with get_demand_db() as conn:
		cur = conn.cursor()
		cur.execute("DELETE FROM demand;")  # sqlite does not implement a TRUNCATE command
		for row in transfer_demand + sales_demand:
			cur.execute(
				f"""INSERT INTO demand ('{"', '".join(row.keys())}') VALUES ('{"', '".join(row.values())}')"""
			)


def dict_factory(cursor: sqlite3.Cursor, row: dict) -> frappe._dict:
	d = frappe._dict({})
	for idx, col in enumerate(cursor.description):
		d[col[0]] = row[idx]
	return d


def get_demand_db() -> sqlite3.Connection:
	path = pathlib.Path(f"{get_site_path()}/demand.db").resolve()
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
					parent text,
					warehouse text,
					name text,
					item_code text,
					delivery_date int,
					modified int,
					net_required_qty real,
					actual_qty real,
					status text
					assigned text
				)
			"""
		)
		cur.execute(
			"""
				CREATE INDEX idx_key
				ON demand(key);
			"""
		)
		cur.execute(
			"""
				CREATE INDEX idx_warehouse
				ON demand(warehouse);
			"""
		)
		cur.execute(
			"""
				CREATE INDEX idx_item_code
				ON demand(item_code);
			"""
		)
		cur.execute(
			"""
				CREATE INDEX delivery_date
				ON demand(delivery_date);
			"""
		)

		return sqlite3.connect(path)


def modify_demand(doc: "Document", method: str | None = None):
	with get_demand_db() as conn:
		conn.row_factory = dict_factory
		cur = conn.cursor()
		for row in doc.items:
			warehouse_field, qty_field = "warehouse", "stock_qty"
			if doc.doctype == "Stock Entry" and method == "submit":
				warehouse_field, qty_field = "t_warehouse", "transfer_qty"
			elif doc.doctype == "Stock Entry" and method == "cancel":
				warehouse_field, qty_field = "s_warehouse", "transfer_qty"

			row_qty = row.get(qty_field)
			result = cur.execute(
				f"""
			SELECT * FROM demand WHERE item_code = '{row.item_code}' AND warehouse = '{row.get(warehouse_field)} ORDER BY delivery_date ASC';
			"""
			)
			rows = result.fetchall()

			for r in rows:
				if r.actual_qty == r.net_required_qty:
					continue
				update_qty = row_qty
				if row_qty > r.net_required_qty:
					row_qty = row_qty - r.net_required_qty
					update_qty = r.net_required_qty
				result = cur.execute(
					f"""
				UPDATE demand SET actual_qty = '{r.net_required_qty}' WHERE key = '{r.key}';
				"""
				)
		conn.commit()
