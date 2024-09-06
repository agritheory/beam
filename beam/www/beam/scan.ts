// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import onScan from 'onscan.js'
import { type Router, useRouter } from 'vue-router'

import type { FormContext, ListContext } from './types/index.js'

interface BeamWindow extends Window {
	scanHandler: ScanHandler
}
declare const frappe: any
declare const window: BeamWindow

export function useScan() {
	const router = useRouter()
	const scanHandler = new ScanHandler(router)
	return { scanHandler }
}

class ScanHandler {
	router: Router
	scanner: onScan

	constructor(router: Router) {
		this.router = router

		if (
			!window.hasOwnProperty('scanHandler') ||
			!window.scanHandler.hasOwnProperty('scanner') ||
			!window.scanHandler.scanner.isAttachedTo(document)
		) {
			let me = this
			this.scanner = onScan.attachTo(document, {
				onScan: async function (sCode: string, iQty: number) {
					await me.prepareContext()
					await me.getScannedContext(sCode, iQty)
				},
			})
			window.scanHandler = this
		}
	}

	async prepareContext() {
		if (!frappe.boot.beam) {
			frappe.boot.beam = await frappe.xcall('beam.beam.scan.config.get_scan_doctypes')
		}
	}

	getContext() {
		let context = {}

		const meta = this.router.currentRoute.value.meta
		if (meta.view === 'list' && frappe.boot.beam.listview.includes(meta.doctype)) {
			context = { listview: meta.doctype }
		} else if (meta.view === 'form' && frappe.boot.beam.frm.includes(meta.doctype)) {
			// TODO: replace `cur_frm` with current active document
			context = { frm: meta.doctype, doc: cur_frm.doc }
		}

		return context
	}

	async getScannedContext(sCode: string, iQty: number) {
		const context = this.getContext()

		try {
			const response: (FormContext | ListContext)[] = await frappe.xcall('beam.beam.scan.scan', {
				barcode: sCode,
				current_qty: iQty,
				context,
			})

			if (response && response.length > 0) {
				let fn: Function
				const action = response[0].action
				if (action in frappe.boot.beam.client) {
					const path: string = frappe.boot.beam.client[action][0]
					// call (first) custom built callback registered in hooks
					fn = path.split('.').reduce((previous, current) => previous[current], window)
				} else {
					fn = this[String(action)] // TODO: this only calls the first function
				}
				return fn(response)
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
		const doc = cur_frm.doc // TODO: replace `cur_frm` with current active document

		barcode_context.forEach(field => {
			if (
				!doc.items.some(row => {
					if (
						doc.doctype === 'Stock Entry' &&
						[
							'Send to Subcontractor',
							'Material Transfer for Manufacture',
							'Material Transfer',
							'Material Receipt',
							'Manufacture',
						].includes(doc.stock_entry_type)
					) {
						return row.item_code === field.context.item_code || row.handling_unit
					}
					return (
						(row.item_code === field.context.item_code && row.stock_qty === field.context.stock_qty) ||
						row.handling_unit === field.context.handling_unit
					)
				})
			) {
				if (!doc.items.length || !doc.items[0].item_code) {
					doc.items = []
				}
				let child = cur_frm.add_child('items', field.context)
				if (doc.doctype === 'Stock Entry') {
					frappe.model.set_value(child.doctype, child.name, 's_warehouse', field.context.warehouse)
				}
			} else {
				for (let row of doc.items) {
					if (
						doc.doctype === 'Stock Entry' &&
						[
							'Send to Subcontractor',
							'Material Transfer for Manufacture',
							'Material Transfer',
							'Material Receipt',
							'Manufacture',
						].includes(doc.stock_entry_type) &&
						row.item_code === field.context.item_code &&
						!row.handling_unit
					) {
						frappe.model.set_value(row.doctype, row.name, field.field, field.target)
						continue
					}
					if (
						(row.item_code === field.context.item_code && row.stock_qty === field.context.stock_qty) ||
						row.handling_unit === field.context.handling_unit
					) {
						if (doc.doctype === 'Stock Entry') {
							if (field.field === 'basic_rate') {
								cur_frm.events.set_basic_rate(cur_frm, row.doctype, row.name)
							} else {
								frappe.model.set_value(row.doctype, row.name, field.field, field.target)
							}
						}
					}
				}
			}
		})

		cur_frm.refresh_field('items')
	}

	set_warehouse(barcode_context: FormContext[]) {
		const source_warehouses = ['Material Consumption for Manufacture', 'Material Issue']
		const target_warehouses = ['Material Receipt', 'Manufacture']
		const both_warehouses = [
			'Material Transfer for Manufacture',
			'Material Transfer',
			'Send to Subcontractor',
			'Repack',
		]

		const context = barcode_context[0]
		const doc = cur_frm.doc // TODO: replace `cur_frm` with current active document

		if (context.doctype === 'Stock Entry') {
			const entry_type = doc.stock_entry_type
			if (source_warehouses.includes(entry_type)) {
				cur_frm.set_value('from_warehouse', context.target)
				for (let row of doc.items) {
					frappe.model.set_value(row.doctype, row.name, 's_warehouse', context.target)
				}
			} else if (target_warehouses.includes(entry_type)) {
				cur_frm.set_value('to_warehouse', context.target)
				for (let row of doc.items) {
					frappe.model.set_value(row.doctype, row.name, 't_warehouse', context.target)
				}
			} else if (both_warehouses.includes(entry_type)) {
				cur_frm.set_value('from_warehouse', context.target)
				cur_frm.set_value('to_warehouse', context.target)
				for (let row of doc.items) {
					frappe.model.set_value(row.doctype, row.name, 's_warehouse', context.target)
					frappe.model.set_value(row.doctype, row.name, 't_warehouse', context.target)
				}
			}
		}
	}

	add_or_increment(barcode_context: FormContext[]) {
		const context = barcode_context[0]
		const doc = cur_frm.doc // TODO: replace `cur_frm` with current active document

		// if not item code, add row
		// else find last row with item code and increment
		if (
			!doc.items.some(row => {
				return (
					(row.item_code === context.context.item_code && !row.handling_unit) || row.barcode === context.context.barcode
				)
			})
		) {
			if (!doc.items.length || !doc.items[0].item_code) {
				doc.items = []
			}
			const row = cur_frm.add_child('items', context.context)
			// a first-time scan of an item in Stock Entry does not automatically set the rate, so run it manually
			if (doc.doctype === 'Stock Entry') {
				cur_frm.events.set_basic_rate(cur_frm, row.doctype, row.name)
			}
		} else {
			for (let row of doc.items) {
				if (
					(row.item_code === context.context.item_code && !row.handling_unit) ||
					row.barcode === context.context.barcode
				) {
					frappe.model.set_value(row.doctype, row.name, 'qty', row.qty + 1)
				}
			}
		}

		cur_frm.refresh_field('items')
	}

	set_item_code_and_handling_unit(barcode_context: FormContext[]) {
		barcode_context.forEach(action => {
			cur_frm.set_value(action.field, action.target)
		})
	}
}
