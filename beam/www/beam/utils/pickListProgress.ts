// Copyright (c) 2026, AgriTheory and contributors
// For license information, please see license.txt

import type { PickListLocation } from '@/types/frappe.js'

export function pickLineTargetQty(row: PickListLocation): number {
	const stockQty = Number(row.stock_qty)
	if (Number.isFinite(stockQty) && stockQty > 0) {
		return stockQty
	}
	return Number(row.qty) || 0
}

export function isPickLineComplete(row: PickListLocation): boolean {
	return (Number(row.picked_qty) || 0) >= pickLineTargetQty(row)
}

export function isPickListFullyPicked(locations: PickListLocation[] | undefined): boolean {
	if (!locations?.length) {
		return false
	}
	return locations.every(isPickLineComplete)
}
