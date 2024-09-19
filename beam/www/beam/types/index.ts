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
}

export type JobCard = ParentDoctype & {
	total_time_in_mins: number
}

export type WorkOrder = ParentDoctype & {
	item_name: string
	qty: number
	produced_qty: number
	planned_start_date: number
	skip_transfer: boolean
	required_items: WorkOrderItem[]
	wip_warehouse: string
	operations: WorkOrderOperation[]
}

export type Workstation = ParentDoctype & {
	production_capacity: number
	status?: string
	workstation_name: string
}

export type WorkOrderOperation = ChildDoctype & {
	name: string
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

export type ListTransferItem = {
	item_name: string
	name: string
	source_warehouse: string
	target_warehouse?: string
	transferred_qty: number
	required_qty: number
	wip_warehouse?: string
}

export type StockEntry = ParentDoctype & {
	item_name: string
	qty: number
	items: ListTransferItem[]
}
