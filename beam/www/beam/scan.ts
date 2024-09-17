// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import { type Router, useRouter } from 'vue-router'

import { useDataStore } from './store.js'
import type { FormContext, ListContext } from './types/index.js'

declare const frappe: any

export function useScan() {
	const router = useRouter()
	const scanHandler = new ScanHandler(router)
	return { scanHandler }
}

class ScanHandler {
	router: Router
	store: ReturnType<typeof useDataStore>

	constructor(router: Router) {
		this.router = router
		this.store = useDataStore()
	}

	async scan(barcode: string, qty: number) {
		await this.prepareContext()
		await this.getScannedContext(barcode, qty)
	}

	async prepareContext() {
		if (!frappe.boot.beam) {
			frappe.boot.beam = await frappe.xcall('beam.beam.scan.config.get_scan_doctypes')
		}
	}

	async getContext() {
		let context = {}

		const route = this.router.currentRoute.value
		if (route.meta.view === 'list' && frappe.boot.beam.listview.includes(route.meta.doctype)) {
			context = { listview: route.meta.doctype }
		} else if (route.meta.view === 'form' /* && frappe.boot.beam.frm.includes(route.meta.doctype) */) {
			await this.store.fetchDoc(route.meta.doctype, route.params.orderId.toString())
			context = { frm: route.meta.doctype, doc: this.store.doc }
		}

		return context
	}

	async getScannedContext(barcode: string, qty: number) {
		const context = await this.getContext()

		try {
			const response: (FormContext | ListContext)[] = await frappe.xcall('beam.beam.scan.scan', {
				barcode,
				current_qty: qty,
				context,
			})

			if (response && response.length > 0) {
				let fn: Function
				const action = response[0].action
				if (action in frappe.boot.beam.client) {
					const path: string = frappe.boot.beam.client[action][0]
					// call (first) custom built callback registered in hooks
					fn = path.split('.').reduce((previous, current) => previous[current], window)
					return await fn(response)
				} else {
					return await this[action](response) // TODO: this only calls the first function
				}
			}
		} catch (error) {
			// TODO: handle API error
			console.error(error)
		}
	}

	route(barcode_context: ListContext[]) {
		// TODO: re-route to formview
	}

	filter(barcode_context: ListContext[]) {
		// TODO: apply filters to listview
	}

	add_or_associate(barcode_context: FormContext[]) {
		barcode_context.forEach(async field => {
			const is_stock_entry =
				this.store.doc.doctype === 'Stock Entry' &&
				[
					'Send to Subcontractor',
					'Material Transfer for Manufacture',
					'Material Transfer',
					'Material Receipt',
					'Manufacture',
				].includes(this.store.doc.stock_entry_type)

			const existing_rows = this.store.doc.items.filter(row => {
				if (is_stock_entry) {
					return row.item_code === field.context.item_code || row.handling_unit
				} else {
					return (
						(row.item_code === field.context.item_code && row.stock_qty === field.context.stock_qty) ||
						row.handling_unit === field.context.handling_unit
					)
				}
			})

			if (existing_rows.length > 0) {
				this.store.$patch(state => {
					for (const row of existing_rows) {
						for (const item of state.doc.items) {
							if (item.name === row.name) {
								item[field.field] = field.target

								// TODO: should this happen on the client side?
								// if (state.doc.doctype === 'Stock Entry' && field.field === 'basic_rate') {
								// 	cur_frm.events.set_basic_rate(cur_frm, row.doctype, row.name)
								// }

								break
							}
						}
					}
				})
			} else {
				this.store.$patch(state => {
					if (state.doc.doctype === 'Stock Entry') {
						field.context.s_warehouse = field.context.warehouse
					}

					// TODO: make sure the other metadata is also present
					const item = { ...field.context, idx: state.doc.items.length + 1 }
					state.doc.items.push(item)
				})
			}
		})
	}

	set_warehouse(barcode_context: FormContext[]) {
		const context = barcode_context[0]
		if (context.doctype !== 'Stock Entry') {
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

		const entry_type = this.store.doc.stock_entry_type
		if (source_warehouses.includes(entry_type)) {
			this.store.$patch(state => {
				state.doc.from_warehouse = context.target
				for (const row of state.doc.items) {
					row.s_warehouse = context.target
				}
			})
		} else if (target_warehouses.includes(entry_type)) {
			this.store.$patch(state => {
				state.doc.to_warehouse = context.target
				for (const row of state.doc.items) {
					row.t_warehouse = context.target
				}
			})
		} else if (both_warehouses.includes(entry_type)) {
			this.store.$patch(state => {
				state.doc.from_warehouse = context.target
				state.doc.to_warehouse = context.target
				for (const row of state.doc.items) {
					row.s_warehouse = context.target
					row.t_warehouse = context.target
				}
			})
		}
	}

	async add_or_increment(barcode_context: FormContext[]) {
		const context = barcode_context[0]

		// if not item code, add row
		// else find last row with item code and increment
		const existing_rows = this.store.doc.items.filter(
			row =>
				(row.item_code === context.context.item_code && !row.handling_unit) || row.barcode === context.context.barcode
		)

		if (existing_rows.length > 0) {
			this.store.$patch(state => {
				for (const row of existing_rows) {
					for (const item of state.doc.items) {
						if (item.name === row.name) {
							item.qty += 1
							break
						}
					}
				}
			})
		} else {
			this.store.$patch(state => {
				// TODO: make sure the other metadata is also present
				const item = { ...context.context, idx: state.doc.items.length + 1 }
				state.doc.items.push(item)

				// TODO: should this happen on the client side?
				// if (state.doc.doctype === 'Stock Entry') {
				// 	cur_frm.events.set_basic_rate(cur_frm, row.doctype, row.name)
				// }
			})
		}
	}

	set_item_code_and_handling_unit(barcode_context: FormContext[]) {
		barcode_context.forEach(action => {
			this.store.$patch(state => {
				state.doc[action.field] = action.target
			})
		})
	}
}
