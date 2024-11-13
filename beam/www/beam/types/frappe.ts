// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import type { StoreMetadata } from '@/types/store.js'

export type DocActionResponse<T> = {
	data?: T
	exception?: string
	response?: Response
}

export type ParentDoctype = StoreMetadata & {
	creation?: string
	docstatus?: number
	doctype?: string
	modified_by?: string
	modified?: string
	name?: string
	owner?: string
}

export type ChildDoctypeMeta = ParentDoctype & {
	idx?: number
	parent?: string
	parenttype?: string
	parentfield?: string
}

export type ChildDoctype = ChildDoctypeMeta & {
	// may not exist for all child doctypes
	barcode?: string
	handling_unit?: string
	item_code?: string
	item_name?: string
	qty?: number
	stock_qty?: number
	warehouse?: string
}

export type JobCard = ParentDoctype & {
	total_time_in_mins: number
}

export type StockEntry = ParentDoctype & {
	stock_entry_type: string

	from_warehouse?: string
	items?: StockEntryItem[]
	purpose?: string
	to_warehouse?: string
}

export type StockEntryItem = ChildDoctype & {
	s_warehouse?: string
	t_warehouse?: string
	transferred_qty?: number
}

export type WorkOrder = ParentDoctype & {
	planned_start_date: string
	qty: number

	item_name?: string
	produced_qty?: number
	skip_transfer?: boolean
	wip_warehouse?: string
	operations?: WorkOrderOperation[]
	required_items?: WorkOrderItem[]
}

export type WorkOrderOperation = ChildDoctype & {
	operation: string
	time_in_mins: number

	actual_operation_time?: number
	completed_qty?: number
	description?: string
}

export type WorkOrderItem = ChildDoctype & {
	required_qty?: number
	source_warehouse?: string
	transferred_qty?: number
}

export type Workstation = ParentDoctype & {
	production_capacity: number
	workstation_name: string

	status?: string
}

export type PurchaseReceipt = ParentDoctype & {
	items: PurchaseReceiptItem[]
}

export type PurchaseReceiptItem = ChildDoctype & {
	qty?: number
	warehouse?: string
}

export type DeliveryNote = ParentDoctype & {
	items: DeliveryNoteItem[]
}

export type DeliveryNoteItem = ChildDoctype & {
	qty: number
	warehouse?: string
}

export type ParentDoctypesWithItems = DeliveryNote | JobCard | PurchaseReceipt | StockEntry | WorkOrder
export type ParentDoctypes = ParentDoctypesWithItems & Workstation
