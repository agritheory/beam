// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import { defineStore } from 'pinia'

import { useBeamStore } from '@/stores/beam.js'
import type { FormContext, ListContext, StockEntry } from '@/types/index.js'

export const useScanStore = defineStore('scan', () => {
	const store = useBeamStore()

	const scan = async (barcode: string, qty: number) => {
		const response = await store.scan(barcode, qty)
		if (response && response.length > 0) {
			let fn: Function
			const action = response[0].action

			const scanHooks = store.config.client
			if (scanHooks.length > 0 && action in scanHooks) {
				const path: string = scanHooks[action][0]
				// call (first) custom built callback registered in hooks
				fn = path.split('.').reduce((previous, current) => previous[current], window)
				return await fn(response)
			} else {
				return await actions[action](response) // TODO: this only calls the first function
			}
		}
	}

	const route = (barcode_context: ListContext[]) => {
		// TODO: re-route to formview; use store router
	}

	const filter = (barcode_context: ListContext[]) => {
		// TODO: apply filters to listview; use store router
	}

	const add_or_associate = (barcode_context: FormContext[]) => {
		barcode_context.forEach(async action => {
			const parentfield = action.parentfield || 'items'
			const is_stock_entry =
				store.form.doctype === 'Stock Entry' &&
				[
					'Send to Subcontractor',
					'Material Transfer for Manufacture',
					'Material Transfer',
					'Material Receipt',
					'Manufacture',
				].includes((store.form as StockEntry).stock_entry_type)

			const existing_rows = store.form[parentfield].filter(row => {
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
				store.$patch(state => {
					for (const row of existing_rows) {
						for (const item of state.form[parentfield]) {
							if (item.name === row.name) {
								item[action.field] = action.target
								break
							}
						}
					}
				})
			} else {
				store.$patch(state => {
					state.form[parentfield].push({
						item_code: action.context.item_code,
						qty: 1,
						[action.field]: action.target,
					})
				})
			}
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
		})
	}

	const add_or_increment = async (barcode_context: FormContext[]) => {
		barcode_context.forEach(async action => {
			const parentfield = action.parentfield || 'items'
			const existing_rows = store.form[parentfield].filter(
				row =>
					(row.item_code === action.context.item_code && !row.handling_unit) || row.barcode === action.context.barcode
			)

			if (existing_rows.length > 0) {
				store.$patch(state => {
					for (const row of existing_rows) {
						for (const item of state.form[parentfield]) {
							if (item.name === row.name) {
								item.transferred_qty = (item.transferred_qty ?? 0) + 1
								break
							}
						}
					}
				})
			} else {
				const source_warehouses = ['Material Consumption for Manufacture', 'Material Issue']
				const target_warehouses = ['Material Receipt', 'Manufacture']
				const both_warehouses = [
					'Material Transfer for Manufacture',
					'Material Transfer',
					'Send to Subcontractor',
					'Repack',
				]

				store.$patch(state => {
					const item = {
						item_code: action.context.item_code,
						qty: 1,
						[action.field]: action.target,
					}

					if (action.doctype === 'Stock Entry') {
						const entry_type = (state.form as StockEntry).stock_entry_type
						if (source_warehouses.includes(entry_type)) {
							item.s_warehouse = action.context.warehouse
						} else if (target_warehouses.includes(entry_type)) {
							item.t_warehouse = action.context.warehouse
						} else if (both_warehouses.includes(entry_type)) {
							item.s_warehouse = action.context.warehouse
							item.t_warehouse = action.context.warehouse
						}
					}

					state.form[parentfield].push(item)
				})
			}
		})
	}

	const set_item_code_and_handling_unit = (barcode_context: FormContext[]) => {
		barcode_context.forEach(action => {
			store.$patch(state => {
				state.form[action.field] = action.target
			})
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

	return { scan }
})
