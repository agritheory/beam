// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import { defineStore } from 'pinia'
import { computed } from 'vue'

import { useBeamStore } from '@/stores/beam.js'
import type {
	FormContext,
	ListContext,
	ParentDoctypesForStockTransfer,
	PurchaseReceipt,
	StockEntry,
	StockEntryItem,
} from '@/types/index.js'

export const useScanStore = defineStore('scan', () => {
	const store = useBeamStore()

	const documentId = computed(() => {
		const currentRoute = store.router.currentRoute.value
		return currentRoute.params.id || currentRoute.query.id || ''
	})

	const mappedDoc = computed(() => store.cache.mappers[documentId.value])

	const scan = async (barcode: string, qty: number) => {
		const response = await store.scan(barcode, qty)
		if (response && response.length > 0) {
			let fn: Function
			const action = response[0].action

			const scanHooks = store.scanner.config.client
			if (action in scanHooks) {
				const path: string = scanHooks[action][0]
				// call (first) custom built callback registered in hooks
				fn = path.split('.').reduce((previous, current) => previous[current], window)
				return await fn(response)
			} else {
				return await actions[action](response) // TODO: this only calls the first function
			}
		}
	}

	const add_or_associate = (barcode_context: FormContext[]) => {
		const is_stock_entry =
			mappedDoc.value.doctype === 'Stock Entry' &&
			[
				'Send to Subcontractor',
				'Material Transfer for Manufacture',
				'Material Transfer',
				'Material Receipt',
				'Manufacture',
			].includes((mappedDoc.value as StockEntry).stock_entry_type)

		barcode_context.forEach(async action => {
			const existing_rows = mappedDoc.value.items.filter(row => {
				if (is_stock_entry) {
					return row.item_code === action.context.item_code || row.handling_unit
				} else {
					return (
						(row.item_code === action.context.item_code && row.stock_qty === action.context.stock_qty) ||
						row.handling_unit === action.context.handling_unit
					)
				}
			})

			if (existing_rows.length > 0) {
				for (const row of existing_rows) {
					if (action.field === 'qty') {
						if (row.doctype === 'Stock Entry Detail') {
							row[action.field] = Math.min((row as StockEntryItem).transfer_qty, action.target)
						}
					} else {
						row[action.field] = action.target
					}
				}
			} else {
				if (mappedDoc.value.doctype === 'Purchase Receipt') {
					;(mappedDoc.value as PurchaseReceipt).items.push({
						item_code: action.context.item_code,
						received_qty: 1,
						[action.field]: action.target,
					})
				} else {
					;(mappedDoc.value as Exclude<ParentDoctypesForStockTransfer, PurchaseReceipt>).items.push({
						item_code: action.context.item_code,
						qty: 1,
						[action.field]: action.target,
					})
				}
			}

			store.$patch(state => (state.cache.mappers[documentId.value] = mappedDoc.value))
		})
	}

	const add_or_increment = (barcode_context: FormContext[]) => {
		barcode_context.forEach(async action => {
			const existing_rows = mappedDoc.value.items.filter(
				row =>
					(row.item_code === action.context.item_code && !row.handling_unit) ||
					row.barcode === action.context.barcode ||
					row.item_code === action.context.doc.item_code
			)

			const itemQtyFieldMap = {
				'Delivery Note Item': 'delivered_qty',
				'Purchase Receipt Item': 'received_qty',
				'Stock Entry Detail': 'qty',
			}

			if (existing_rows.length > 0) {
				const field = itemQtyFieldMap[action.doctype] || 'qty'
				for (const row of existing_rows) {
					row[field] = row[field] + 1
				}
			} else if (action.doctype === 'Stock Entry') {
				const source_warehouses = ['Material Consumption for Manufacture', 'Material Issue']
				const target_warehouses = ['Material Receipt', 'Manufacture']
				const both_warehouses = [
					'Material Transfer for Manufacture',
					'Material Transfer',
					'Send to Subcontractor',
					'Repack',
				]

				const item: StockEntryItem = {
					item_code: action.context.item_code,
					qty: 1,
					[action.field]: action.target,
				}

				const entry_type = (mappedDoc.value as StockEntry).stock_entry_type
				if (source_warehouses.includes(entry_type)) {
					item.s_warehouse = action.context.warehouse
				} else if (target_warehouses.includes(entry_type)) {
					item.t_warehouse = action.context.warehouse
				} else if (both_warehouses.includes(entry_type)) {
					item.s_warehouse = action.context.warehouse
					item.t_warehouse = action.context.warehouse
				}

				;(mappedDoc.value as StockEntry).items.push(item)
			} else {
				const item: StockEntryItem = {
					item_code: action.context.doc.item_code,
					qty: 1,
				}

				;(mappedDoc.value as StockEntry).items.push(item)
			}
			store.$patch(state => (state.cache.mappers[documentId.value] = mappedDoc.value))
		})
	}

	const filter = (barcode_context: ListContext[]) => {
		// TODO: apply filters to listview; use store router
	}

	const route = (barcode_context: ListContext[]) => {
		// TODO: re-route to formview; use store router
	}

	const set_item_code_and_handling_unit = (barcode_context: FormContext[]) => {
		barcode_context.forEach(action => {
			store.$patch(state => {
				state.form[action.field] = action.target
			})
		})
	}

	const set_warehouse = (barcode_context: FormContext[]) => {
		barcode_context.forEach(async action => {
			if (action.doctype !== 'Stock Entry') {
				return
			}

			const source_warehouses = ['Material Consumption for Manufacture', 'Material Issue']
			const target_warehouses = ['Material Receipt', 'Manufacture']
			const both_warehouses = [
				'Material Transfer for Manufacture',
				'Material Transfer',
				'Send to Subcontractor',
				'Repack',
			]

			const entry_type = (store.form as StockEntry).stock_entry_type
			if (entry_type) {
				store.$patch(state => {
					const form = state.form as StockEntry
					if (source_warehouses.includes(entry_type)) {
						form.from_warehouse = action.target
						for (const row of form.items) {
							row.s_warehouse = action.target
						}
					} else if (target_warehouses.includes(entry_type)) {
						form.to_warehouse = action.target
						for (const row of form.items) {
							row.t_warehouse = action.target
						}
					} else if (both_warehouses.includes(entry_type)) {
						form.from_warehouse = action.target
						form.to_warehouse = action.target
						for (const row of form.items) {
							row.s_warehouse = action.target
							row.t_warehouse = action.target
						}
					}
				})
			} else {
				const warehouse = barcode_context[0].context.doc.name
				if (!(mappedDoc.value as StockEntry).from_warehouse) {
					;(mappedDoc.value as StockEntry).from_warehouse = warehouse
				} else if (!(mappedDoc.value as StockEntry).to_warehouse) {
					;(mappedDoc.value as StockEntry).to_warehouse = warehouse
				}

				store.$patch(state => (state.cache.mappers[documentId.value] = mappedDoc.value))
			}
		})
	}

	const actions = {
		add_or_associate,
		add_or_increment,
		filter,
		route,
		set_item_code_and_handling_unit,
		set_warehouse,
	}

	return {
		// getters
		documentId,
		mappedDoc,

		// actions
		scan,
	}
})
