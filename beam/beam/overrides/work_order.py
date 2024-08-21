import frappe
from erpnext.manufacturing.doctype.work_order.work_order import (
	close_work_order as erpnext_close_work_order,
)

from beam.beam.demand.demand import modify_demand


@frappe.whitelist()
def close_work_order(work_order, status):
	status = erpnext_close_work_order(work_order, status)
	work_order = frappe.get_doc("Work Order", work_order)
	modify_demand(work_order)
	return status
