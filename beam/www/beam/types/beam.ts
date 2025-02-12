// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import type { ListViewItem } from '@stonecrop/beam'
import type { ButtonHTMLAttributes, CSSProperties, HTMLAttributes } from 'vue'

import type { ParentDoctypesForStockTransfer, StockEntry } from '@/types/frappe.js'

export interface BeamWindow extends Window {
	frappe: any
	scanner: any
}

export type BeamHome = {
	routes: ListViewItem[]
	company: string
}

export type BeamCache = {
	mappers: {
		move?: StockEntry
		repack?: StockEntry
		[key: string]: ParentDoctypesForStockTransfer
	}
}

export type ControlButton = {
	action: HTMLAttributes['onClick']
	label: string

	color?: {
		background: CSSProperties['backgroundColor']
		text: CSSProperties['color']
	}
	disabled?: ButtonHTMLAttributes['disabled']
	hidden?: boolean
}

export type Demand = {
	allocated_date: null
	allocated_qty: number
	assigned: string
	bom_no: string
	company: string
	creation: string
	customer: string
	delivery_date: null
	demand: string
	doctype: string
	idx: number
	item_code: string
	item_warehouse: string
	key: string
	modified: null
	name: string
	net_required_qty: number
	parent: string
	production_item: string
	status: string
	stock_uom: string
	total_required_qty: number
	warehouse: string
}

export type Receive = {
	assigned: null
	company: string
	creation: string
	doctype: string
	idx: number
	item_code: string
	key: string
	modified: string
	name: string
	parent: string
	received_qty: number
	rejected_qty: number
	schedule_date: string
	status: string
	stock_qty: number
	stock_uom: string
	supplier: string
	warehouse: string
}
