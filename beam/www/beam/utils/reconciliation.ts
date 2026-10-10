// Copyright (c) 2026, AgriTheory and contributors
// For license information, please see license.txt

import type { StockEntryItem } from '@/types'
import { itemListLine } from '@/utils/itemListLine'

export type ReconciliationListRow = StockEntryItem & {
	warehouse?: string
	label?: string
	description?: string
	debounce?: number
	count?: { count: number | null }
}

export type ReconciliationSaveMode = 'counted_only' | 'include_zero_uncounted'

export function hasCountedQuantity(rows: ReconciliationListRow[]): boolean {
	return rows.some(row => row.count?.count !== null && row.count?.count !== undefined)
}

export function uncountedRowCount(rows: ReconciliationListRow[]): number {
	return rows.filter(row => row.count?.count == null).length
}

export function buildReconciliationItems(
	rows: ReconciliationListRow[],
	warehouse: string,
	mode: ReconciliationSaveMode
) {
	const items: Record<string, unknown>[] = []

	for (const row of rows) {
		const counted = row.count?.count
		if (counted == null) {
			if (mode === 'include_zero_uncounted') {
				items.push(reconciliationItemPayload(row, warehouse, 0))
			}
			continue
		}
		items.push(reconciliationItemPayload(row, warehouse, counted))
	}

	return items
}

const listOnlyFields = ['count', 'label', 'description', 'debounce'] as const

function reconciliationItemPayload(row: ReconciliationListRow, warehouse: string, qty: number) {
	const payload: Record<string, unknown> = { ...row, warehouse: row.warehouse || warehouse, qty }
	for (const field of listOnlyFields) delete payload[field]
	return payload
}

export function warehouseRowFromApi(apiItem: StockEntryItem, warehouse: string): ReconciliationListRow {
	const rowWarehouse = apiItem.warehouse || warehouse
	const line = itemListLine({ ...apiItem, warehouse: rowWarehouse })

	return {
		...apiItem,
		qty: undefined,
		warehouse: rowWarehouse,
		label: line.label,
		description: line.description,
		count: {
			count: null,
		},
		debounce: 1000,
	}
}
