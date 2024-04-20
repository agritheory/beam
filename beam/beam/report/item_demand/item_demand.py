# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import datetime
from time import localtime

import frappe

from beam.beam.demand import dict_factory, get_demand_db


def execute(filters=None):
	columns, data = [], []
	return get_columns(filters), get_data(filters)


def get_columns(filters):
	return [
		{"fieldname": "doctype", "fieldtype": "Link", "options": "DocType", "hidden": True},
		{
			"label": frappe._("Document"),
			"fieldname": "parent",
			"fieldtype": "Dynamic Link",
			"options": "doctype",
			"width": "250px",
		},
		{
			"label": frappe._("Warehouse"),
			"fieldname": "warehouse",
			"fieldtype": "Dynamic Link",
			"options": "doctype",
			"width": "150px",
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
			"label": frappe._("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Dynamic Link",
			"options": "doctype",
			"width": "150px",
		},
		{
			"label": frappe._("Net Req Qty"),
			"fieldname": "net_required_qty",
			"fieldtype": "Float",
			"width": "100px",
			"align": "Right",
		},
		{
			"label": frappe._("Actual Qty"),
			"fieldname": "actual_qty",
			"fieldtype": "Float",
			"width": "100px",
			"align": "Right",
		},
		{
			"label": frappe._("Status"),
			"fieldname": "status",
			"fieldtype": "Data",
			"width": "150px",
		},
		{
			"label": frappe._("Assigned"),
			"fieldname": "assigned",
			"fieldtype": "Data",
			"width": "150px",
		},
	]


def get_data(filters):
	with get_demand_db() as conn:
		conn.row_factory = dict_factory
		cur = conn.cursor()
		result = cur.execute("SELECT * FROM demand")
		rows = result.fetchall()

	for row in rows:
		row.delivery_date = datetime.datetime(*localtime(row.delivery_date)[:6])
	return rows
