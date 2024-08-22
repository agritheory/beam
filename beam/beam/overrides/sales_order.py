from erpnext.selling.doctype.sales_order.sales_order import SalesOrder

from beam.beam.demand.demand import add_demand_allocation, remove_demand_allocation


class BEAMSalesOrder(SalesOrder):
	def update_status(self, status):
		super().update_status(status)
		if self.docstatus == 1:
			if status == "Draft":  # status for resuming a held or closed sales order
				add_demand_allocation(self.name)
			elif status in ("Completed", "Cancelled", "Closed", "On Hold"):
				remove_demand_allocation(self.name)
