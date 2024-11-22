// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import type { ButtonHTMLAttributes, CSSProperties, HTMLAttributes } from 'vue'

import type { ParentDoctypesForStockTransfer } from '@/types/frappe.js'

export interface BeamWindow extends Window {
	frappe: any
	scanner: any
}

export type BeamHome = {
	routes: ListViewItem[]
	company: string
}

export type BeamCache = {
	mappers: Record<string, ParentDoctypesForStockTransfer>
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

export type Demand = {
	key: string;
	demand: string;
	doctype: string;
	company: string;
	parent: string;
	warehouse: string;
	production_item: string;
	bom_no: string;
	name: string;
	idx: number;
	item_code: string;
	item_warehouse: string;
	allocated_date: null;
	delivery_date: null;
	modified: null;
	stock_uom: string;
	allocated_qty: number;
	net_required_qty: number;
	total_required_qty: number;
	status: string;
	assigned: string;
	creation: Date;
	customer: string;
}

export type Receive = {
	key:           string;
    doctype:       string;
    company:       string;
    parent:        string;
    warehouse:     string;
    name:          string;
    idx:           number;
    item_code:     string;
    schedule_date: Date;
    modified:      Date;
    stock_uom:     string;
    stock_qty:     number;
    received_qty:  number;
    supplier:      string;
    status:        string;
    assigned:      null;
    creation:      Date;
    rejected_qty:  number;
}
