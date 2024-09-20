// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

// beam view interfaces
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

// scan interfaces
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

export type ScanContext = {
	frm?: string
	listview?: string
}

export type ScanConfig = {
	client?: Record<string, string[]>
	frm?: string[]
	listview?: string[]
	scannable_doctypes?: string[]
}

// frappe document interfaces
export type ParentDoctypeMeta = {
	creation?: string
	doctype?: string
	modified_by?: string
	modified?: string
	name?: string
	owner?: string
}

export type ChildDoctypeMeta = ParentDoctypeMeta & {
	idx?: number
	parent?: string
	parenttype?: string
	parentfield?: string
}

export type ParentDoctype = ParentDoctypeMeta & {
	// exists for most sales/purchase/stock documents
	items?: ChildDoctype[]

	// exists for stock entry only
	from_warehouse?: string
	stock_entry_type?: string
	to_warehouse?: string
}

export type ChildDoctype = ChildDoctypeMeta & {
	// may not exist for all child doctypes
	barcode?: string
	handling_unit?: string
	item_code?: string
	qty?: number
	stock_qty?: number
	warehouse?: string

	// exists for stock entry only
	s_warehouse?: string
	t_warehouse?: string
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
