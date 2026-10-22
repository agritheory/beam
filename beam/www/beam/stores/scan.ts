// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import { defineStore } from 'pinia'
import { computed } from 'vue'

import { useBeamStore } from '@/stores/beam.js'
import type { ChildDoctype, PickList } from '@/types/frappe.js'
import { defaultCompany } from '@/utils/company.js'
import { useBeamToast } from '@/utils/toast.js'
import type {
	DeliveryNoteItem,
	FormContext,
	ListContext,
	ParentDoctypesForStockTransfer,
	PurchaseReceipt,
	ScanContext,
	StockEntry,
	StockEntryItem,
	StockReconciliation,
} from '@/types/index.js'

declare const frappe: any

const pickListWarehouseGates: Record<string, string | null> = {}

export const useScanStore = defineStore('scan', () => {
	const store = useBeamStore()
	const toast = useBeamToast()

	const documentId = computed(() => {
		const currentRoute = store.router.currentRoute.value
		return currentRoute.params.id || currentRoute.query.id || currentRoute.name || ''
	})

	const mappedDoc = computed(() => store.cache.mappers[documentId.value])

	const scanContextForRequest = (): ScanContext => {
		const base: ScanContext = { ...store.scanner.context }
		const mapKey = documentId.value
		if (!mapKey) {
			return base
		}
		const mapped = store.cache.mappers[mapKey] as ParentDoctypesForStockTransfer | undefined
		if (!mapped) {
			return base
		}
		// Send a plain copy: reactive proxies don't serialize every field.
		const doc = JSON.parse(JSON.stringify(mapped)) as Record<string, unknown>
		if (base.frm === 'Stock Entry') {
			if (!doc.doctype) {
				doc.doctype = 'Stock Entry'
			}
			if (!doc.purpose && doc.stock_entry_type) {
				doc.purpose = doc.stock_entry_type
			}
			if (!doc.company) {
				doc.company = defaultCompany()
			}
		}
		const context: ScanContext = { ...base, doc }
		if (context.frm === 'Work Order' && mapped.doctype === 'Stock Entry') {
			context.frm = 'Stock Entry'
		}
		return context
	}

	const scan = async (barcode: string, qty: number) => {
		store.scanner.lastScan = barcode
		store.scanner.lastDocType = ''
		const currentRoute = store.router.currentRoute.value
		if (currentRoute.name === 'pick_list') {
			const pickListId = currentRoute.params.id.toString()
			const mapped = store.cache.mappers[pickListId] as PickList | undefined
			const pickedQuantities = Object.fromEntries(
				(mapped?.locations || []).map(location => [String(location.idx), location.picked_qty || 0])
			)
			const result = await frappe.xcall('beam.beam.pick_list.apply_pick_list_scan', {
				pick_list_name: pickListId,
				barcode,
				warehouse_gate: pickListWarehouseGates[pickListId] || null,
				picked_quantities: JSON.stringify(pickedQuantities),
			})
			if (!result?.ok) {
				if (result?.message) {
					toast.error(result.message)
				}
				return
			}
			if (result.warehouse_gate) {
				pickListWarehouseGates[pickListId] = result.warehouse_gate
				store.scanner.lastDocType = `Warehouse: ${result.warehouse_gate}`
				return
			}
			const doc = store.cache.mappers[pickListId] as PickList | undefined
			if (doc && result.idx != null && result.picked_qty != null) {
				pickListWarehouseGates[pickListId] = null
				const row = doc.locations.find(location => location.idx == result.idx)
				if (row) {
					row.picked_qty = result.picked_qty
					store.$patch(state => {
						const mapped = state.cache.mappers[pickListId] as PickList
						mapped.dirty = true
					})
					store.scanner.lastDocType = `${row.item_code}: ${result.picked_qty}`
				}
			}
			return
		}

		const response = await store.scan(barcode, qty, scanContextForRequest())
		if (response && response.length > 0) {
			let fn: Function
			const action = response[0].action
			const ctx = response[0].context as ChildDoctype | undefined
			if (ctx?.doc) {
				store.scanner.lastDocType = `${ctx.doc.doctype}: ${ctx.doc.name}`
			} else if (response[0].parenttype) {
				store.scanner.lastDocType = `${response[0].parenttype}: ${response[0].parent}`
			} else {
				store.scanner.lastDocType = `${response[0].doctype}: ${ctx?.item_code ?? ctx?.warehouse ?? barcode}`
			}

			const scanHooks = store.scanner.config.client

			// an empty array indicates no additional client actions are registered
			if (!Array.isArray(scanHooks) && action in scanHooks) {
				const path = scanHooks[action][0]
				// call (first) custom built callback registered in hooks
				fn = path.split('.').reduce((previous, current) => previous[current], window)
				return await fn(response)
			} else {
				return await actions[action](response) // TODO: this only calls the first function
			}
		}
	}

	const hasScanTarget = () => {
		if (mappedDoc.value?.items) return true
		// The page owning this route has not registered its document yet, so the
		// scan has nowhere to land. Dropping it silently reads to an operator as a
		// scanner that misfired, and to a test as a failure several steps later.
		toast.error('This page is not ready to accept scans yet, please scan again')
		return false
	}

	const add_or_associate = (barcode_context: FormContext[]) => {
		if (!hasScanTarget()) return

		const is_stock_entry =
			mappedDoc.value.doctype === 'Stock Entry' &&
			[
				'Send to Subcontractor',
				'Material Transfer for Manufacture',
				'Material Transfer',
				'Material Receipt',
				'Manufacture',
			].includes((mappedDoc.value as StockEntry).stock_entry_type)

		for (const action of barcode_context) {
			const existing_rows = mappedDoc.value.items.filter(row => {
				if (is_stock_entry) {
					return row.item_code === action.context.item_code || row.handling_unit
				} else {
					// For HU scans, match by item_code alone — HU stock_qty may differ from SO qty
					const isHuScan = action.context.handling_unit != null
					return (
						row.handling_unit === action.context.handling_unit ||
						(row.item_code === action.context.item_code && (isHuScan || row.stock_qty === action.context.stock_qty))
					)
				}
			})
			if (existing_rows.length > 0) {
				for (const row of existing_rows) {
					if (action.field === 'qty') {
						if (row.doctype === 'Stock Entry Detail') {
							row[action.field] = Math.min((row as StockEntryItem).transfer_qty!, action.target)
						}
					} else if (action.field === 'delivered_qty' && (row as DeliveryNoteItem).qty != null) {
						;(row as DeliveryNoteItem).delivered_qty = Math.min(action.target, (row as DeliveryNoteItem).qty)
					} else if (
						action.field === 'handling_unit' &&
						mappedDoc.value.doctype === 'Delivery Note' &&
						(row as DeliveryNoteItem).qty != null
					) {
						row.handling_unit = action.target
						const huQty = action.context.stock_qty ?? action.context.qty ?? 0
						;(row as DeliveryNoteItem).delivered_qty = Math.min((row as DeliveryNoteItem).qty, huQty)
					} else {
						row[action.field] = action.target
					}
				}
			} else {
				if (mappedDoc.value.doctype === 'Purchase Receipt') {
					;(mappedDoc.value as PurchaseReceipt).items.push({
						item_code: action.context.item_code,
						item_name: action.context.item_name,
						received_qty: 1,
						[action.field]: action.target,
					})
				} else {
					;(mappedDoc.value as Exclude<ParentDoctypesForStockTransfer, PurchaseReceipt>).items.push({
						item_code: action.context.item_code,
						item_name: action.context.item_name,
						qty: 1,
						[action.field]: action.target,
					})
				}
			}

			store.$patch(state => (state.cache.mappers[documentId.value] = mappedDoc.value))
		}
	}

	const add_or_increment = (barcode_context: FormContext[]) => {
		if (!hasScanTarget()) return

		if (documentId.value === 'stock-reconciliation' && store.reconciliationItemScan) {
			for (const action of barcode_context) {
				const ctx = action.context
				store.reconciliationItemScan({
					item_code: ctx.item_code ?? ctx.doc?.item_code ?? '',
					item_name: ctx.item_name ?? ctx.doc?.item_name,
					stock_uom: ctx.stock_uom ?? ctx.doc?.stock_uom,
					valuation_rate: ctx.valuation_rate,
					warehouse: (mappedDoc.value as StockReconciliation)?.set_warehouse,
				})
			}
			return
		}

		for (const action of barcode_context) {
			const existing_rows = mappedDoc.value.items.filter(
				row =>
					(row.item_code === action.context.item_code && !row.handling_unit) ||
					row.barcode === action.context.barcode ||
					row.item_code === action.context.doc?.item_code
			)

			const itemQtyFieldMap = {
				'Delivery Note Item': 'delivered_qty',
				'Purchase Receipt Item': 'received_qty',
				'Stock Entry Detail': 'qty',
			}

			if (existing_rows.length > 0) {
				const field = itemQtyFieldMap[action.doctype] || 'qty'
				for (const row of existing_rows) {
					if (field !== 'qty' && row.qty) {
						row[field] = Math.min(row[field] + 1, row.qty)
					} else {
						row[field] = (row[field] || 0) + 1
					}
				}
			} else if (action.doctype === 'Stock Entry Detail' || action.doctype === 'Stock Entry') {
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
					item_code: action.context.item_code ?? action.context.doc?.item_code,
					stock_uom: action.context.stock_uom ?? action.context.doc?.stock_uom,
					qty: 1,
					[action.field]: action.target,
				}

				;(mappedDoc.value as StockEntry).items.push(item)
			}
			store.$patch(state => (state.cache.mappers[documentId.value] = mappedDoc.value))
		}
	}

	const filter = (barcode_context: ListContext[]) => {
		// TODO: apply filters to listview; use store router
	}

	const route = (barcode_context: ListContext[]) => {
		// only route based on the last action in hooks
		const action = barcode_context && barcode_context.at(-1)
		if (action?.route) {
			store.router.push(action.route)
		}
	}

	const set_item_code_and_handling_unit = (barcode_context: FormContext[]) => {
		for (const action of barcode_context) {
			store.$patch(state => {
				state.form[action.field] = action.target
			})
		}
	}

	const set_warehouse = (barcode_context: FormContext[]) => {
		for (const action of barcode_context) {
			if (action.doctype === 'Stock Reconciliation Item') {
				;(mappedDoc.value as StockReconciliation).set_warehouse = action.context.warehouse
				store.$patch(state => (state.cache.mappers[documentId.value] = mappedDoc.value))
				continue
			}

			if (action.doctype !== 'Stock Entry' || !mappedDoc.value) continue

			const source_warehouses = ['Material Consumption for Manufacture', 'Material Issue']
			const target_warehouses = ['Material Receipt', 'Manufacture']
			const both_warehouses = [
				'Material Transfer for Manufacture',
				'Material Transfer',
				'Send to Subcontractor',
				'Repack',
			]

			const entry = mappedDoc.value as StockEntry
			const entry_type = entry.stock_entry_type
			const warehouse = action.context.warehouse
			if (entry_type && source_warehouses.includes(entry_type)) {
				entry.from_warehouse = warehouse
				for (const row of entry.items) row.s_warehouse = warehouse
			} else if (entry_type && target_warehouses.includes(entry_type)) {
				entry.to_warehouse = warehouse
				for (const row of entry.items) row.t_warehouse = warehouse
			} else if (entry_type && both_warehouses.includes(entry_type)) {
				entry.from_warehouse = warehouse
				entry.to_warehouse = warehouse
				for (const row of entry.items) {
					row.s_warehouse = warehouse
					row.t_warehouse = warehouse
				}
			} else if (!entry.from_warehouse) {
				entry.from_warehouse = warehouse
			} else if (!entry.to_warehouse) {
				entry.to_warehouse = warehouse
			}

			store.$patch(state => (state.cache.mappers[documentId.value] = mappedDoc.value))
		}
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
