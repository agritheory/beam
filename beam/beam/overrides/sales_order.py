import frappe
from erpnext.selling.doctype.sales_order.sales_order import update_status as erpnext_update_status

from beam.beam.demand.demand import modify_demand


@frappe.whitelist()
def update_status(status, name):
	erpnext_update_status(status, name)
	sales_order = frappe.get_doc("Sales Order", name)
	if status == "Closed":
		modify_demand(sales_order)
	return status
