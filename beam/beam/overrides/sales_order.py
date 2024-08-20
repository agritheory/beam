import frappe
from erpnext.selling.doctype.sales_order.sales_order import update_status as erpnext_update_status

from beam.beam.demand.demand import build_demand_map


@frappe.whitelist()
def update_status(status, name):
	erpnext_update_status(status, name)
	if status == "Closed":
		build_demand_map()
	return status
