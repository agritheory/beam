// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import { useDataStore } from './store.js'
import type { FormContext, ListContext, FrappeWindow } from './types/index.js'

export function useScan() {
	const scanHandler = new ScanHandler()
	window.scan = scanHandler
	return { scanHandler }
}

class ScanHandler {
	store: ReturnType<typeof useDataStore>

	constructor() {
		this.store = useDataStore()
	}

	async scan(barcode: string, qty: number) {
		const response = await this.store.scan(barcode, qty)
		if (response && response.length > 0) {
			let fn: Function
			const action = response[0].action

			if (action in this.store.config.client) {
				const path = this.store.config.client[action][0]
				// call (first) custom built callback registered in hooks
				fn = path.split('.').reduce((previous, current) => previous[current], window)
				return await fn(response)
			} else {
				return await this[action](response) // TODO: this only calls the first function
			}
		}
	}

	route(barcode_context: ListContext[]) {
		// TODO: re-route to formview; use store router
	}

	filter(barcode_context: ListContext[]) {
		// TODO: apply filters to listview; use store router
	}

	add_or_associate(barcode_context: FormContext[]) {
		barcode_context.forEach(async action => {
			const is_stock_entry =
				this.store.form.value.doctype === 'Stock Entry' &&
				[
					'Send to Subcontractor',
					'Material Transfer for Manufacture',
					'Material Transfer',
					'Material Receipt',
					'Manufacture',
				].includes(this.store.form.value.stock_entry_type)

			const existing_rows = this.store.form.value.items.filter(row => {
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
				this.store.$patch(state => {
					for (const row of existing_rows) {
						for (const item of state.form.value.items) {
							if (item.name === row.name) {
								item[action.field] = action.target
								break
							}
						}
					}
				})
			} else {
				this.store.$patch(state => {
					state.form.value.items.push({
						item_code: action.context.item_code,
						qty: 1,
						[action.field]: action.target,
					})
				})
			}
		})
	}

	set_warehouse(barcode_context: FormContext[]) {
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

			const entry_type = this.store.form.value.stock_entry_type
			if (source_warehouses.includes(entry_type)) {
				this.store.$patch(state => {
					state.form.value.from_warehouse = action.target
					for (const row of state.form.value.items) {
						row.s_warehouse = action.target
					}
				})
			} else if (target_warehouses.includes(entry_type)) {
				this.store.$patch(state => {
					state.form.value.to_warehouse = action.target
					for (const row of state.form.value.items) {
						row.t_warehouse = action.target
					}
				})
			} else if (both_warehouses.includes(entry_type)) {
				this.store.$patch(state => {
					state.form.value.from_warehouse = action.target
					state.form.value.to_warehouse = action.target
					for (const row of state.form.value.items) {
						row.s_warehouse = action.target
						row.t_warehouse = action.target
					}
				})
			}
		})
	}

	async add_or_increment(barcode_context: FormContext[]) {
		barcode_context.forEach(async action => {
			const parentfield = action.parentfield || 'items'
			const existing_rows = this.store.form[parentfield].filter(
				row =>
					(row.item_code === action.context.item_code && !row.handling_unit) || row.barcode === action.context.barcode
			)

			if (existing_rows.length > 0) {
				this.store.$patch(state => {
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

				this.store.$patch(state => {
					const item = {
						item_code: action.context.item_code,
						qty: 1,
						[action.field]: action.target,
					}

					if (action.doctype === 'Stock Entry') {
						const entry_type = state.form.stock_entry_type
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

	set_item_code_and_handling_unit(barcode_context: FormContext[]) {
		barcode_context.forEach(action => {
			this.store.$patch(state => {
				state.form[action.field] = action.target
			})
		})
	}
}
