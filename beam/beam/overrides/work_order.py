import frappe
from erpnext.manufacturing.doctype.work_order.work_order import (
	close_work_order as erpnext_close_work_order,
)

from beam.beam.demand.demand import build_demand_map


@frappe.whitelist()
def close_work_order(work_order, status):
	status = erpnext_close_work_order(work_order, status)
	build_demand_map()
	return status
