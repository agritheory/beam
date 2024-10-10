# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import calendar
import datetime
from time import localtime
from typing import TypedDict

from frappe.utils import get_datetime


class Base(TypedDict, total=False):
	assigned: str
	company: str
	creation: str | float | datetime.datetime
	doctype: str
	item_code: str
	key: str
	modified: str | float | datetime.datetime
	name: str
	parent: str
	stock_uom: str
	warehouse: str
	workstation: str


class Demand(TypedDict, Base, total=False):
	delivery_date: str | float | datetime.datetime
	total_required_qty: str | float  # demand quantity that hasn't been satisfied


class Allocation(TypedDict, Base, total=False):
	allocated_date: str | float | datetime.datetime
	allocated_qty: str | float
	demand: str
	is_manual: str | float
	status: str

	# not directly available in the database, but computed using the demand row
	delivery_date: str | float | datetime.datetime
	net_required_qty: str | float  # demand quantity that has yet to be allocated
	total_required_qty: str | float  # demand quantity that hasn't been satisfied


class Receiving(TypedDict, Base, total=False):
	schedule_date: str | float | datetime.datetime
	stock_qty: str | float


def get_epoch_from_datetime(dt: str | float | datetime.datetime | None = None) -> int | float:
	if isinstance(dt, (int, float)):
		return dt

	datetime_obj = get_datetime(dt)
	time_tuple = datetime_obj.timetuple()
	return calendar.timegm(time_tuple)


def get_datetime_from_epoch(seconds: str | float) -> datetime.datetime | None:
	if isinstance(seconds, str):
		return get_datetime(seconds)

	local_epoch = localtime(seconds)
	local_epoch_list = local_epoch[:6]
	return datetime.datetime(*local_epoch_list)
