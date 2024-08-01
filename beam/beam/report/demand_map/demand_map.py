# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import datetime
from time import localtime

import frappe
from frappe.utils.data import flt

from beam.beam.demand.demand import dict_factory, get_balance_qty_from_sle, get_demand_db


def execute(filters=None):
	return get_columns(filters), get_data(filters)


def get_columns(filters):
	return [
		{"fieldname": "key", "fieldtype": "Data", "hidden": True},
		{"fieldname": "doctype", "fieldtype": "Link", "options": "DocType", "hidden": True},
		{
			"label": frappe._("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": "250px",
		},
		{
			"label": frappe._("Demand Warehouse"),
			"fieldname": "demand_warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": "200px",
		},
		{
			"label": frappe._("Source Warehouse"),
			"fieldname": "source_warehouse",
			"fieldtype": "Data",
			"width": "200px",
		},
		{
			"label": frappe._("Document"),
			"fieldname": "parent",
			"fieldtype": "Dynamic Link",
			"options": "doctype",
			"width": "200px",
		},
		{"fieldname": "name", "fieldtype": "Data", "hidden": True},
		{
			"label": frappe._("Delivery Date"),
			"fieldname": "delivery_date",
			"fieldtype": "Datetime",
			"width": "200px",
			"align": "Right",
		},
		{
			"label": frappe._("Total Req Qty"),
			"fieldname": "total_required_qty",
			"fieldtype": "Float",
			"width": "100px",
			"align": "Right",
		},
		{
			"label": frappe._("Net Req Qty"),
			"fieldname": "net_required_qty",
			"fieldtype": "Float",
			"width": "100px",
			"align": "Right",
		},
		{
			"label": frappe._("Allocated"),
			"fieldname": "allocated_qty",
			"fieldtype": "Float",
			"width": "100px",
			"align": "Right",
		},
		{
			"label": frappe._("Stock UOM"),
			"fieldname": "stock_uom",
			"fieldtype": "Data",
			"width": "100px",
		},
		{
			"label": frappe._("Status"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": "150px",
			"align": "center",
		},
		{
			"label": frappe._("Assigned"),
			"fieldname": "assigned",
			"fieldtype": "Data",
			"width": "150px",
		},
	]


def get_data(filters):
	rows = []
	with get_demand_db() as conn:
		conn.row_factory = dict_factory
		cur = conn.cursor()
		filter_query = ""
		if filters.item_code:
			filter_query = f"WHERE item_code = '{filters.item_code}'"
		demand = cur.execute(
			f"""
			SELECT
				d.*,
				COALESCE(
					(SELECT SUM(a.allocated_qty) FROM allocation a WHERE a.demand = d.key),
					0
				) AS allocated_qty
			FROM
				demand d
			{filter_query}
			ORDER BY delivery_date ASC;
		"""
		).fetchall()

		# TODO: implement sort filters here
		indent_counter = 0
		for row in demand:
			row.indent = 0
			row.delivery_date = datetime.datetime(*localtime(row.delivery_date)[:6])
			row.demand_warehouse = row.pop("warehouse")
			rows.append(row)
			allocations = cur.execute(
				f"""
				SELECT * FROM allocation WHERE demand = '{row.key}'"""
			).fetchall()
			row.allocated_qty = sum(flt(allocation.allocated_qty) for allocation in allocations)
			for allocation in allocations:
				allocation.indent = 1
				allocation.delivery_date = datetime.datetime(*localtime(allocation.allocated_date)[:6])
				allocation.source_warehouse = allocation.pop("warehouse")
				if allocation.source_warehouse != row.demand_warehouse:
					allocation.source_warehouse = (
						f'<span style="color: orange">{allocation.source_warehouse}</span>'
					)

				rows.append(allocation)
	return rows
