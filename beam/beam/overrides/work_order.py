from erpnext.manufacturing.doctype.work_order.work_order import WorkOrder

from beam.beam.demand.demand import add_demand_allocation, remove_demand_allocation


class BEAMWorkOrder(WorkOrder):
	def update_status(self, status=None):
		super().update_status(status)
		if self.docstatus == 1:
			if status == "Resumed":
				add_demand_allocation(self.name)
			elif status in ("Completed", "Cancelled", "Closed", "Stopped"):
				remove_demand_allocation(self.name)
