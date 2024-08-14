export type ParentDoctype = {
	creation: string
	modified_by: string
	modified: string
	name: string
	owner: string
}

export type ChildDoctype = ParentDoctype & {
	idx: number
	parent: string
	parenttype: string
	parentfield: string
}

export type JobCard = ParentDoctype & {
	total_time_in_mins: number
}

export type WorkOrder = ParentDoctype & {
	item_name: string
	qty: number

	operations: WorkOrderOperation[]
}

export type Workstation = ParentDoctype & {
	production_capacity: number
	status?: string
	workstation_name: string
}

export type WorkOrderOperation = ChildDoctype & {
	actual_operation_time: number
	completed_qty: number
	description?: string
	operation: string
}