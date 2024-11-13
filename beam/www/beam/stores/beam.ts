// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { RouteLocationNormalized } from 'vue-router'

import { useHttpStore } from '@/stores/http.js'
import type {
	BeamCache,
	BeamHome,
	FormContext,
	ListContext,
	ParentDoctypes,
	ParentDoctypesForStockTransfer,
	ScanConfig,
	ScanContext,
	StockEntry,
} from '@/types/index.js'

declare const frappe: any

const BEAM_HOME_URL = '/api/method/beam.beam.doctype.beam_settings.beam_settings.get_beam_home'
const LOGOUT_URL = '/api/method/logout'
const MAPPED_STOCK_ENTRY_URL = '/api/method/erpnext.manufacturing.doctype.work_order.work_order.make_stock_entry'
const NEW_DOC_URL = '/api/method/beam.www.beam.make_new_doc'
const PURCHASE_DEMAND_URL = '/api/method/beam.beam.demand.receiving.get_receiving_demand'
const SALES_DEMAND_URL = '/api/method/beam.beam.demand.demand.get_demand'
const SCAN_CONFIG_URL = '/api/method/beam.beam.scan.config.get_scan_doctypes'
const SCAN_URL = 'beam.beam.scan.scan' // frappe.xcall doesn't require prefix

export const useBeamStore = defineStore('beam', () => {
	const httpStore = useHttpStore()

	const recordsPerPage = 20
	const cache = ref<BeamCache>({ mappers: {} })
	const config = ref<ScanConfig>({})
	const context = ref<ScanContext>({})
	const form = ref<Partial<ParentDoctypes>>({})

	const getScanDoctypes = async (params?: Record<string, any>) => {
		const response = await httpStore.get(SCAN_CONFIG_URL, params)
		const { message }: { message: ScanConfig } = await response.json()
		config.value = message
		return { data: message }
	}

	// TODO: vue-router's useRoute() composable is not working as intended here, so accepting route input
	const setForm = async (currentRoute: RouteLocationNormalized) => {
		form.value = {}

		const meta = currentRoute.meta
		if (meta.view === 'form' && config.value.frm.includes(meta.doctype)) {
			let docname: string
			if (currentRoute.params.id) {
				docname = currentRoute.params.id.toString()
				form.value = await getOne<ParentDoctypes>(meta.doctype, docname)
			} else if (meta.doctype) {
				if (currentRoute.query.id) {
					docname = currentRoute.query.id.toString()
				}
				form.value = await makeNewDoc<ParentDoctypesForStockTransfer>(meta.doctype, docname)
			}
		}
	}

	const setScanContext = async (currentRoute: RouteLocationNormalized) => {
		const meta = currentRoute.meta
		if (meta.view === 'list' && config.value.listview.includes(meta.doctype)) {
			context.value = { listview: meta.doctype }
		} else if (meta.view === 'form' && config.value.frm.includes(meta.doctype)) {
			context.value = { frm: meta.doctype }
		}
	}

	const getOne = async <T>(doctype: string, name: string) => {
		const url = `/api/resource/${doctype}/${name}`
		const response = await httpStore.get(url)
		const { data }: { data: T } = await response.json()
		return data
	}

	const getAll = async <T>(doctype: string, params?: Record<string, any>, page?: number) => {
		if (page) {
			const start = (page - 1) * recordsPerPage
			const end = start + recordsPerPage
			params = { ...params, limit_start: start, limit_page_length: end }
		}

		const url = `/api/resource/${doctype}`
		const response = await httpStore.get(url, params)
		const { data }: { data: T } = await response.json()
		return data
	}

	const getHome = async (params?: Record<string, any>) => {
		const response = await httpStore.get(BEAM_HOME_URL, params)
		const { message }: { message: BeamHome } = await response.json()
		return { data: message }
	}

	const getDemand = async (params?: Record<string, any>) => {
		// automatically fetch all pages of demand data based on parameters
		const response = await httpStore.get(SALES_DEMAND_URL, params)
		const { message } = await response.json()
		return { data: message }
	}

	const getReceiving = async (params?: Record<string, any>) => {
		// automatically fetch all pages of demand data based on parameters
		const response = await httpStore.get(PURCHASE_DEMAND_URL, params)
		const { message } = await response.json()
		return { data: message }
	}

	const scan = async (barcode: string, qty: number): Promise<(FormContext | ListContext)[]> => {
		try {
			return await frappe.xcall(SCAN_URL, {
				barcode,
				current_qty: qty,
				context: context.value,
			})
		} catch (error) {
			// TODO: handle API error
			console.error(error)
		}

		return []
	}

	const insert = async <T>(doctype: string, body: T) => {
		const url = `/api/resource/${doctype}`
		const response = await httpStore.post(url, body)
		const { data, exception }: { data: T; exception: string } = await response.json()
		if (response.ok) form.value.dirty = false
		alert(response.ok ? 'Document created' : exception)
		return { data, exception, response }
	}

	const save = async <T>(doctype: string, name: string, body: Partial<T>) => {
		const url = `/api/resource/${doctype}/${name}`
		const response = await httpStore.post(url, body)
		const { data, exception }: { data: T; exception: string } = await response.json()
		if (response.ok) form.value.dirty = false
		alert(response.ok ? 'Document updated' : exception)
		return { data, exception, response }
	}

	const submit = async <T>(doctype: string, name: string) => {
		const url = `/api/resource/${doctype}/${name}`
		const response = await httpStore.put(url, { docstatus: 1 })
		const { data, exception }: { data: T; exception: string } = await response.json()
		if (response.ok) form.value.dirty = false
		alert(response.ok ? 'Document status changed to Submitted' : exception)
		return { data, exception, response }
	}

	const cancel = async <T>(doctype: string, name: string) => {
		const url = `/api/resource/${doctype}/${name}`
		const response = await httpStore.put(url, { docstatus: 2 })
		const { data, exception }: { data: T; exception: string } = await response.json()
		if (response.ok) form.value.dirty = false
		alert(response.ok ? 'Document status changed to Cancelled' : exception)
		return { data, exception, response }
	}

	const makeNewDoc = async <T>(doctype: string, docname?: string) => {
		const response = await httpStore.post(NEW_DOC_URL, { doctype, docname })
		const { message }: { message: T } = await response.json()
		return message
	}

	const getMappedStockEntry = async (data: Record<string, any>) => {
		// return a work order object with attached stock entry/ies and job card(s)
		const response = await httpStore.post(MAPPED_STOCK_ENTRY_URL, data)
		const { message }: { message: StockEntry } = await response.json()
		if (!message) {
			alert('Error: Could not map Work Order to Stock Entry')
			return
		}
		// initialize pending stock entry items with zero quantity
		message.items.map(item => {
			item.qty = 0
		})
		return message
	}

	const logout = async () => {
		await httpStore.get(LOGOUT_URL)
		window.location.href = '/login?redirect-to=/beam#'
	}

	return {
		// state
		cache,
		config,
		context,
		form,

		// store context actions
		getScanDoctypes,
		setForm,
		setScanContext,

		// document workflow actions
		cancel,
		insert,
		save,
		submit,

		// other api actions
		getAll,
		getDemand,
		getHome,
		getMappedStockEntry,
		getOne,
		getReceiving,
		logout,
		makeNewDoc,
		scan,
	}
})
