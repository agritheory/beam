import calendar
import copy
import datetime
import pathlib
import sqlite3
from collections import deque
from itertools import takewhile
from time import localtime
from typing import TYPE_CHECKING, Union

import frappe
from frappe.utils import get_site_path
from frappe.utils.data import flt, get_datetime
from frappe.utils.nestedset import get_descendants_of
from frappe.utils.synchronization import filelock

if TYPE_CHECKING:
	from erpnext.accounts.doctype.purchase_invoice.purchase_invoice import PurchaseInvoice
	from erpnext.accounts.doctype.sales_invoice.sales_invoice import SalesInvoice
	from erpnext.stock.doctype.delivery_note.delivery_note import DeliveryNote
	from erpnext.stock.doctype.purchase_receipt.purchase_receipt import PurchaseReceipt
	from erpnext.stock.doctype.stock_entry.stock_entry import StockEntry
	from erpnext.stock.doctype.stock_reconciliation.stock_reconciliation import StockReconciliation


def get_balance_qty_from_sle(item_code, warehouse=None, company=None) -> float | list:
	if not company and not warehouse:
		company = frappe.defaults.get_defaults().get("company")

	if warehouse:
		_warehouse = warehouse

	if not warehouse or frappe.get_cached_value("Warehouse", warehouse, "is_group") == 1:
		root_warehouse = frappe.get_all(
			"Warehouse",
			{"is_group": 1, "parent_warehouse": ["is", "not set"], "company": company},
			pluck="name",
		)[0]
		_warehouse = f"""{"', '".join(get_descendant_warehouses(frappe.get_doc('BEAM Settings', company), root_warehouse))}"""

	balance_qty = frappe.db.sql(
		f"""
		SELECT qty_after_transaction, warehouse FROM `tabStock Ledger Entry`
		WHERE item_code = %(item_code)s
		AND warehouse IN ('{_warehouse}')
		AND is_cancelled = 0
		ORDER BY posting_date desc, posting_time desc, creation desc
		""",
		{"item_code": item_code},
		as_dict=True,
	)

	if not warehouse:
		return balance_qty

	return flt(balance_qty[0].qty_after_transaction) if balance_qty else 0.0


def build_demand_map() -> None:
	output = []
	transfer_demand = frappe.db.sql(
		"""
			SELECT
				'Work Order' AS doctype,
				`tabWork Order`.name AS parent,
				`tabWork Order`.company,
				`tabWork Order`.wip_warehouse AS warehouse,
				`tabWork Order Item`.name,
				`tabWork Order Item`.item_code,
				`tabWork Order`.planned_start_date AS delivery_date,
				(`tabWork Order Item`.required_qty - `tabWork Order Item`.transferred_qty) AS total_required_qty,
				`tabItem`.stock_uom
			FROM
				`tabWork Order`
			JOIN
				`tabWork Order Item` ON `tabWork Order`.name = `tabWork Order Item`.parent
			LEFT JOIN
				`tabItem` ON `tabWork Order Item`.item_code = `tabItem`.name
			WHERE
				(`tabWork Order Item`.transferred_qty - `tabWork Order Item`.required_qty) < 0
				AND `tabWork Order`.status = 'Not Started'
			ORDER BY
				`tabWork Order`.planned_start_date, `tabWork Order`.name ASC
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
				`tabSales Order`.company,
				%(default_fg_warehouse)s AS warehouse,
				`tabSales Order Item`.name,
				`tabSales Order Item`.item_code,
				`tabSales Order`.delivery_date,
				(`tabSales Order Item`.stock_qty - `tabSales Order Item`.delivered_qty) AS total_required_qty,
				`tabItem`.stock_uom
			FROM
				`tabSales Order`
			JOIN
				`tabSales Order Item` ON `tabSales Order`.name = `tabSales Order Item`.parent
			LEFT JOIN
				`tabItem` ON `tabSales Order Item`.item_code = `tabItem`.name
			WHERE
				`tabSales Order`.docstatus = 1
				AND `tabSales Order`.status != 'Closed'
				AND (`tabSales Order Item`.stock_qty - `tabSales Order Item`.delivered_qty) > 0
			ORDER BY
				`tabSales Order`.delivery_date, `tabSales Order`.name ASC
		""",
		{"default_fg_warehouse": default_fg_warehouse},
		as_dict=True,
	)
	for row in transfer_demand + sales_demand:
		row.key = frappe.generate_hash()
		row.delivery_date = str(calendar.timegm(get_datetime(row.delivery_date).timetuple()))
		row.total_required_qty = str(row.total_required_qty)
		output.append(row)

	with get_demand_db() as conn:
		cur = conn.cursor()
		cur.execute("DELETE FROM demand;")  # sqlite does not implement a TRUNCATE command
		cur.execute("DELETE FROM allocation;")  # sqlite does not implement a TRUNCATE command
		for row in output:
			cur.execute(
				f"""INSERT INTO demand ('{"', '".join(row.keys())}') VALUES ('{"', '".join(row.values())}')"""
			)

	build_allocation_map()


def build_allocation_map(doc=None, doc_row=None, action=None):
	supply_allocation = []
	demand_allocation = []

	with get_demand_db() as conn:
		conn.row_factory = dict_factory
		cur = conn.cursor()
		item_demand_map = frappe._dict({})
		item_query = ""
		if doc_row:
			item_query = f"WHERE item_code = '{doc_row.item_code}'"

		raw_demand = cur.execute(
			f"""
			SELECT
				d.*,
				COALESCE(
				(SELECT SUM(a.allocated_qty) FROM allocation a WHERE a.demand = d.key),
					0
				) AS allocated_qty,
				d.total_required_qty - COALESCE(
					(SELECT SUM(a.allocated_qty) FROM allocation a WHERE a.demand = d.key),
					0
				) AS net_required_qty
			FROM
				demand d
			{item_query}
			ORDER BY delivery_date ASC;
		"""
		).fetchall()
		for d in raw_demand:
			if d.item_code in item_demand_map:
				item_demand_map[d.item_code].append(d)
			else:
				item_demand_map[d.item_code] = [d]

		for _item_code, demand_rows in item_demand_map.items():
			# TODO: make supply fetching respect inventory dimensions
			# TODO: make supply fetching respect accounting dimensions
			demand_queue = deque(demand_rows)
			supply_queue = deque(get_balance_qty_from_sle(_item_code))
			if not any([bool(supply_queue), bool(demand_queue)]):
				continue

			while bool(supply_queue) and bool(demand_queue):
				current_supply = supply_queue[0]
				current_demand = demand_queue[0]

				net_required_qty = current_demand["total_required_qty"] - current_demand["allocated_qty"]
				if current_supply["qty_after_transaction"] >= net_required_qty:
					# Full demand can be met
					allocated_qty = net_required_qty
					demand_allocation.append(
						{
							**new_allocation(current_demand),
							"warehouse": current_supply["warehouse"],
							"demand_doc": current_demand["parent"],
							"allocated_qty": str(allocated_qty),
						}
					)
					current_supply["qty_after_transaction"] -= allocated_qty
					demand_queue.popleft()

					if current_supply["qty_after_transaction"] == 0:
						supply_queue.popleft()
						break
				else:
					# Partial demand is met
					allocated_qty = current_supply["qty_after_transaction"]
					demand_allocation.append(
						{
							**new_allocation(current_demand),
							"warehouse": current_supply.get("warehouse"),
							"allocated_qty": str(allocated_qty),
						}
					)
					current_demand["total_required_qty"] -= allocated_qty
					supply_queue.popleft()

				# Update supply allocation
				supply_allocation.append(
					{
						**new_allocation(current_demand),
						"warehouse": current_supply.get("warehouse"),
						"allocated_qty": str(allocated_qty),
					}
				)

			demand_queue = deque([])
			supply_queue = deque([])

		for allocation in supply_allocation:
			cur.execute(
				f"""INSERT INTO allocation ('{"', '".join(allocation.keys())}') VALUES ('{"', '".join(allocation.values())}')"""
			)


def new_allocation(demand_row):
	return frappe._dict(
		{
			"key": frappe.generate_hash(),
			"demand": demand_row.key,
			"doctype": demand_row.doctype,
			"company": demand_row.company,
			"parent": demand_row.parent,
			"name": demand_row.name,
			"item_code": demand_row.item_code,
			"allocated_date": str(calendar.timegm(get_datetime().timetuple())),
			"modified": str(calendar.timegm(get_datetime().timetuple())),
			"stock_uom": demand_row.stock_uom,
			"status": "Soft Allocated",
			"assigned": demand_row.assigned or "",
		}
	)


def dict_factory(cursor: sqlite3.Cursor, row: dict) -> frappe._dict:
	d = frappe._dict({})
	for idx, col in enumerate(cursor.description):
		d[col[0]] = row[idx]
	return d


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


def modify_allocations(
	doc: Union[
		"DeliveryNote",
		"PurchaseInvoice",
		"PurchaseReceipt",
		"SalesInvoice",
		"StockEntry",
		"StockReconciliation",
	],
	method: str | None = None,
):
	demand_hooks = frappe.get_hooks("demand")
	doctype_matrix = demand_hooks.get(doc.doctype)
	if not doctype_matrix:
		return
	for row in doc.get("items"):
		method_matrix = doctype_matrix.get(method)
		if not method_matrix:
			continue

		for action in method_matrix:
			if action.get("conditions"):
				for key, value in action.get("conditions", {}).items():
					if doc.get(key) != value:
						continue  # TODO remove nested continue
					build_allocation_map(doc=doc, doc_row=row, action=action)


def get_descendant_warehouses(beam_settings, warehouse):
	beam_settings = frappe.get_doc("BEAM Settings", beam_settings).as_dict()
	warehouse_types = []
	if beam_settings.warehouse_types:
		warehouse_types = [wt.warehouse_type for wt in beam_settings.warehouse_types]

	if warehouse_types:
		order_by = "lft"
		limit = None
		lft, rgt = frappe.get_cached_value("Warehouse", warehouse, ["lft", "rgt"])

		if rgt - lft <= 1:
			return []

		descendant_warehouses = frappe.get_list(
			"Warehouse",
			{
				"lft": [">", lft],
				"rgt": ["<", rgt],
				"company": beam_settings.company,
				"warehouse_type": ["not in", warehouse_types],
			},
			"name",
			order_by=order_by,
			limit_page_length=limit,
			ignore_permissions=True,
			pluck="name",
		)
		return descendant_warehouses
	else:
		descendant_warehouses = get_descendants_of(
			"Warehouse", warehouse, ignore_permissions=True, order_by="lft"
		)
		return descendant_warehouses


@frappe.whitelist()
def get_demand(
	company,
	item_code=None,
	warehouse=None,
	workstation=None,
	assigned=None,
	order_by="workstation, assigned",
):
	filters = {}
	if workstation:
		filters["workstation"] = f"{workstation}"
	if item_code:
		filters["item_code"] = f"{item_code}"
	if warehouse:
		filters["warehouse"] = f"{warehouse}"

	d_filters = "AND " + "\nAND ".join([f"d.{key} IN ('{value}')" for key, value in filters.items()])
	a_filters = "AND " + "\nAND ".join([f"a.{key} IN ('{value}')" for key, value in filters.items()])

	# if assigned:
	# 	_filters += f" AND assigned LIKE %{assigned}%"

	with get_demand_db() as conn:
		conn.row_factory = dict_factory
		cur = conn.cursor()
		query = f"""
			SELECT
				d.key,
				'' AS demand,
				d.doctype,
				d.company,
				d.parent,

				d.warehouse,
				d.name,
				d.item_code,
				d.delivery_date AS allocated_date,
				d.delivery_date,

				d.modified,
				d.stock_uom,
				COALESCE(
					(SELECT SUM(a.allocated_qty) FROM allocation a WHERE a.demand = d.key),
					0
				) AS allocated_qty,
				d.total_required_qty - COALESCE(
					(SELECT SUM(a.allocated_qty) FROM allocation a WHERE a.demand = d.key),
					0
				) AS net_required_qty,
				d.total_required_qty,

				'' AS status,
				d.assigned
			FROM demand d
			WHERE allocated_qty <= 0
			{d_filters}
			UNION ALL
			SELECT
				a.key,
				a.demand,
				a.doctype,
				a.company,
				a.parent,

				a.warehouse,
				a.name,
				a.item_code,
				a.allocated_date AS delivery_date,
				a.allocated_date,

				a.modified,
				a.stock_uom,
				a.allocated_qty,
				COALESCE(
					(SELECT d.total_required_qty FROM demand d WHERE a.demand = d.key),
					0
				) -
				COALESCE(
					(SELECT SUM(c.allocated_qty) FROM allocation c WHERE a.demand = c.demand),
					0
				) AS net_required_qty,
				(SELECT d.total_required_qty FROM demand d WHERE a.demand = d.key) AS total_required_qty,

				a.status,
				a.assigned
			FROM allocation a
			WHERE allocated_qty > 0
			{a_filters}
			ORDER BY delivery_date, parent ASC
		"""
		rows = cur.execute(query).fetchall()

		for row in rows:
			row.delivery_date = datetime.datetime(*localtime(row.delivery_date)[:6])
			row.allocated_date = datetime.datetime(*localtime(row.allocated_date)[:6])
			row.modified = datetime.datetime(*localtime(row.modified)[:6])
		return rows
