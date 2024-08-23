import datetime
from typing import TypedDict

import frappe


class Demand(TypedDict, frappe._dict, total=False):
	assigned: str
	company: str
	creation: datetime.datetime
	delivery_date: datetime.datetime
	doctype: str
	item_code: str
	key: str
	modified: datetime.datetime
	name: str
	parent: str
	stock_uom: str
	total_required_qty: float
	warehouse: str


class Allocation(TypedDict, frappe._dict, total=False):
	allocated_date: datetime.datetime
	allocated_qty: float
	assigned: str
	company: str
	creation: datetime.datetime
	delivery_date: datetime.datetime
	demand: str
	doctype: str
	is_manual: float
	item_code: str
	key: str
	modified: datetime.datetime
	name: str
	net_required_qty: float
	parent: str
	status: str
	stock_uom: str
	total_required_qty: float
	warehouse: str
