// Copyright (c) 2026, AgriTheory and contributors
// For license information, please see license.txt

export type InspectionKind = 'gate' | 'hold'
export type InspectionState = 'needed' | 'draft' | 'Accepted' | 'Rejected' | 'released'

export type LineInspection = {
	row: string
	idx?: number
	item_code: string
	kind: InspectionKind
	quality_inspection: string | null
	state: InspectionState
	qi_status?: string | null
	holding_warehouse?: string
	intended_warehouse?: string
	reference_type: string
	reference_name: string
}

export type AwaitingLine = LineInspection & {
	qty?: number
	schedule_date?: string
}

export type InspectionReading = {
	parameter: string
	label: string
	kind: 'numeric' | 'text' | 'passfail'
	hint: string
	values: string[]
}

export type InspectionForm = {
	reference_type: string
	reference_name: string
	purchase_order?: string | null
	row: string
	item_code: string
	item_name: string
	batch_no: string | null
	serial_no: string | null
	sample_size: number
	readings: InspectionReading[]
	editable: boolean
	correction: 'amend' | 'reinspect' | null
	kind: InspectionKind
	quality_inspection: string | null
	status: string
	can_release: boolean
}

export type InspectionSubmitResult = {
	name: string
	status: 'Accepted' | 'Rejected'
	can_release: boolean
	readings?: InspectionReading[]
	quality_inspection?: string
}
