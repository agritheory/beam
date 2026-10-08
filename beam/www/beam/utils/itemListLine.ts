// Copyright (c) 2026, AgriTheory and contributors
// For license information, please see license.txt

export type ItemListLineInput = {
	item_code?: string
	item_name?: string
	warehouse?: string
	source_warehouse?: string
	item_warehouse?: string
	stock_uom?: string
	uom?: string
}

function plainText(value: string): string {
	return value
		.replace(/<[^>]*>/g, ' ')
		.replace(/\s+/g, ' ')
		.trim()
}

export function itemUom(item: Pick<ItemListLineInput, 'stock_uom' | 'uom'>): string {
	return plainText(item.stock_uom || item.uom || '')
}

/** Append unit to warehouse / subtitle text (shown in list description, not on the qty control). */
export function appendUomText(base: string, item: Pick<ItemListLineInput, 'stock_uom' | 'uom'>): string {
	const uom = itemUom(item)
	const text = plainText(base)
	if (!uom) return text
	if (!text) return uom
	return `${text} · ${uom}`
}

/** Document line items: item name as label; warehouse + UOM as subtitle (PR, DN, WO materials). */
export function itemListLine(item: ItemListLineInput): { label: string; description: string } {
	const label = plainText(item.item_name || item.item_code || '')
	const warehouse = plainText(item.warehouse || item.source_warehouse || item.item_warehouse || '')
	const description = appendUomText(warehouse, item)
	return { label, description }
}
