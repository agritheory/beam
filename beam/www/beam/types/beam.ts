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
