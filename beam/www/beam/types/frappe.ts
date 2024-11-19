// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import type { StoreMetadata } from '@/types/store.js'

export type FrappeResponse<T = any> = {
	_exc_source?: string
	_server_messages?: string
	data?: T
	exc_type?: string
	exc?: string
	exception?: string
	home_page?: string
}

export type DocActionResponse<T> = FrappeResponse<T> & {
	response?: Response
}

export type ParentDoctype = StoreMetadata & {
	__islocal?: number
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
	items?: JobCardItem[]
}

export type JobCardItem = ChildDoctype & {
	item_code?: string
	required_qty?: number
	source_warehouse?: string
	transferred_qty?: number
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
	transfer_qty?: number
	transferred_qty?: number
}

export type WorkOrder = ParentDoctype & {
	planned_start_date: string
	production_item: string
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
	workstation?: string
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
	received_qty: number

	qty?: number
	warehouse?: string
}

export type DeliveryNote = ParentDoctype & {
	items: DeliveryNoteItem[]
}

export type DeliveryNoteItem = ChildDoctype & {
	qty: number

	delivered_qty?: number // doesn't exist in the schema, but is used in the app
	warehouse?: string
}

export type ParentDoctypesForStockTransfer = DeliveryNote | PurchaseReceipt | StockEntry
export type ParentDoctypesWithItems = ParentDoctypesForStockTransfer | JobCard | WorkOrder
export type ParentDoctypes = ParentDoctypesWithItems & Workstation
