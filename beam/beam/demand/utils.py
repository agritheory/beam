import calendar
import datetime
from time import localtime
from typing import TypedDict

from frappe.utils import get_datetime


class Demand(TypedDict, total=False):
	assigned: str
	company: str
	creation: datetime.datetime | float
	delivery_date: datetime.datetime | float
	doctype: str
	item_code: str
	key: str
	modified: datetime.datetime | float
	name: str
	parent: str
	stock_uom: str
	total_required_qty: float
	warehouse: str


class Allocation(TypedDict, total=False):
	allocated_date: datetime.datetime | float
	allocated_qty: float
	assigned: str
	company: str
	creation: datetime.datetime | float
	delivery_date: datetime.datetime | float
	demand: str
	doctype: str
	is_manual: float
	item_code: str
	key: str
	modified: datetime.datetime | float
	name: str
	net_required_qty: float
	parent: str
	status: str
	stock_uom: str
	total_required_qty: float
	warehouse: str


def get_epoch_from_datetime(dt: datetime.datetime | float | None = None) -> int | float:
	if isinstance(dt, (int, float)):
		return dt

	datetime_obj = get_datetime(dt)
	time_tuple = datetime_obj.timetuple()
	return calendar.timegm(time_tuple)


def get_datetime_from_epoch(seconds: float) -> datetime.datetime:
	local_epoch = localtime(seconds)
	local_epoch_list = local_epoch[:6]
	return datetime.datetime(*local_epoch_list)
