// Copyright (c) 2026, AgriTheory and contributors
// For license information, please see license.txt

import type { StockEntryItem } from '@/types'

export type ReconciliationListRow = StockEntryItem & {
	warehouse?: string
	label?: string
	debounce?: number
	count?: { count: number | null; uom?: string }
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

function reconciliationItemPayload(row: ReconciliationListRow, warehouse: string, qty: number) {
	const { count, label, debounce, qty: systemQty, ...rest } = row
	void count
	void label
	void debounce
	void systemQty

	return {
		...rest,
		warehouse: rest.warehouse || warehouse,
		qty,
	}
}

export function warehouseRowFromApi(apiItem: StockEntryItem, warehouse: string): ReconciliationListRow {
	const { qty, ...rest } = apiItem
	void qty

	return {
		...rest,
		warehouse: rest.warehouse || warehouse,
		label: apiItem.item_name || apiItem.item_code,
		count: {
			count: null,
			uom: apiItem.stock_uom,
		},
		debounce: 1000,
	}
}
