// Copyright (c) 2026, AgriTheory and contributors
// For license information, please see license.txt

import type { ListViewItem } from '@stonecrop/beam'

import type { LineInspection } from '@/types/inspection'
import { useInspectionStore } from '@/stores/inspection'

export type InspectionListItem = ListViewItem & {
	inspectionState?: string
}

function withInspectionHint(description: string | undefined, hint: string): string {
	if (!description) return hint
	if (description.includes(hint)) return description
	return `${description} · ${hint}`
}

export function applyInspectionLines<T extends ListViewItem>(
	items: T[],
	byKey: Record<string, LineInspection>,
	itemKey: (item: T) => string | undefined = item => (item as { name?: string }).name,
	incomingInspectionItemCodes?: ReadonlySet<string>
): (T & InspectionListItem)[] {
	const inspectionStore = useInspectionStore()
	return items.map(item => {
		const rowName = (item as { name?: string }).name
		const rowIdx = (item as { idx?: number }).idx
		const itemCode = (item as { item_code?: string }).item_code
		let inspection = rowName ? byKey[rowName] : undefined
		if (!inspection && rowIdx != null) {
			inspection = byKey[`idx:${rowIdx}`]
		}
		if (!inspection) {
			const key = itemKey(item)
			if (key) inspection = byKey[key]
		}
		if (!inspection && itemCode) {
			const matches = Object.values(byKey).filter(line => line.item_code === itemCode)
			if (matches.length === 1) {
				inspection = matches[0]
			} else if (matches.length > 1) {
				inspection =
					matches.find(line => line.row === rowName || line.idx === rowIdx) ?? matches[0]
			}
		}
		if (!inspection && itemCode && incomingInspectionItemCodes?.has(itemCode)) {
			const hint = inspectionStatusHint('needed')
			return {
				...item,
				description: withInspectionHint(item.description, hint),
				inspectionState: 'needed',
			}
		}
		if (!inspection) return item
		const hint = inspectionStatusHint(inspection.state)
		const description = withInspectionHint(item.description, hint)
		const updated: T & InspectionListItem = {
			...item,
			description,
			inspectionState: inspection.state,
		}
		if (inspection.reference_name) {
			updated.linkComponent = 'ListAnchor'
			updated.route = inspectionStore.inspectionHash(
				inspection.reference_type,
				inspection.reference_name,
				inspection.row,
				inspection.state
			)
		}
		return updated
	})
}

/** Submitted QI exists but failed — blocks ERPNext receive if Stock Settings use Stop. */
export function gateLineNeedsAttention(line: LineInspection): boolean {
	if (line.kind !== 'gate') return false
	return line.state === 'needed' || line.state === 'draft' || line.state === 'Rejected'
}

/** Gate line still needs mobile inspection work (no submitted QI yet). */
export function gateLineNeedsInspectionWork(line: LineInspection): boolean {
	if (line.kind !== 'gate') return false
	return line.state === 'needed' || line.state === 'draft'
}

export type InspectionLinkTarget = {
	reference_type: string
	reference_name: string
	row: string
	state?: LineInspection['state']
}

/** First gate line that still needs inspection entry (draft / not started). */
export function firstPendingGateInspection(
	receiptName: string | undefined,
	byRow: Record<string, LineInspection>,
	items: { name?: string; item_code?: string; idx?: number }[] | undefined,
	incomingInspectionItemCodes?: ReadonlySet<string>
): InspectionLinkTarget | null {
	if (!receiptName || receiptName.startsWith('new-')) return null

	const seenRows = new Set<string>()
	const gateLines: LineInspection[] = []
	for (const line of Object.values(byRow)) {
		if (!line.row || seenRows.has(line.row)) continue
		if (!gateLineNeedsInspectionWork(line)) continue
		seenRows.add(line.row)
		gateLines.push(line)
	}
	gateLines.sort((a, b) => (a.idx ?? 0) - (b.idx ?? 0))

	const first = gateLines[0]
	if (first) {
		return {
			reference_type: first.reference_type || 'Purchase Receipt',
			reference_name: first.reference_name || receiptName,
			row: first.row,
			state: first.state,
		}
	}

	if (!items?.length || !incomingInspectionItemCodes?.size) return null
	for (const item of items) {
		if (item.item_code && incomingInspectionItemCodes.has(item.item_code) && item.name) {
			return {
				reference_type: 'Purchase Receipt',
				reference_name: receiptName,
				row: item.name,
				state: 'needed',
			}
		}
	}
	return null
}

export function indexInspectionsByRow(lines: LineInspection[]): Record<string, LineInspection> {
	const out: Record<string, LineInspection> = {}
	for (const line of lines) {
		out[line.row] = line
		if (line.idx != null) {
			out[`idx:${line.idx}`] = line
		}
	}
	return out
}

export function indexInspectionsByItemCode(lines: LineInspection[]): Record<string, LineInspection> {
	return Object.fromEntries(lines.map(line => [line.item_code, line]))
}

export function inspectionStatusHint(state: string | undefined): string {
	switch (state) {
		case 'needed':
			return 'Inspection required'
		case 'draft':
			return 'Inspection in progress'
		case 'Accepted':
			return 'Inspection accepted'
		case 'Rejected':
			return 'Inspection rejected'
		case 'released':
			return 'Released from quarantine'
		default:
			return 'Quality inspection'
	}
}

export function inspectionAriaLabel(state: string | undefined): string {
	switch (state) {
		case 'needed':
			return 'Inspection required'
		case 'draft':
			return 'Inspection draft'
		case 'Accepted':
			return 'Inspection accepted'
		case 'Rejected':
			return 'Inspection rejected'
		case 'released':
			return 'Released from quarantine'
		default:
			return 'Quality inspection'
	}
}
