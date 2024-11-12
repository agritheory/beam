// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import { ScanHandler } from '@/scan.js'

export interface BeamWindow extends Window {
	frappe: any
	scan: ScanHandler
	scanner: any
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

export type BeamHome = {
	routes: ListViewItem[]
	company: string
}
