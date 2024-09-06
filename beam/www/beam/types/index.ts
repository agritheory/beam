// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

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

	// may not exist for all child doctypes
	barcode?: string
	handling_unit?: string
	item_code?: string
	stock_qty?: number
	warehouse?: string
}

export type JobCard = ParentDoctype & {
	total_time_in_mins: number
}

export type WorkOrder = ParentDoctype & {
	item_name: string
	qty: number
	produced_qty: number

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
	time_in_mins?: number
}

export type ListViewItem = {
	label: string
	description?: string
	count?: {
		count: number
		of: number
		uom?: string
	}
	checked?: boolean
	linkComponent?: string
	route?: string
}

export type BaseContext = {
	action: string
	doctype: string
	field: string
	target: string
}

export type FormContext = BaseContext & {
	context: ChildDoctype
}

export type ListContext = BaseContext & {
	context: string
}
