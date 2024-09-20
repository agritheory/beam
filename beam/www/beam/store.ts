// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import { defineStore } from 'pinia'
import { computed, ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import type {
	FormContext,
	JobCard,
	ListContext,
	ScanConfig,
	ScanContext,
	StockEntry,
	WorkOrder,
	Workstation,
} from '@/types/index.js'

declare const frappe: any

export const useDataStore = defineStore('data', () => {
	const route = useRoute()

	const config = ref<ScanConfig>({})
	const context = ref<ScanContext>({})
	const form = ref<Partial<JobCard | WorkOrder | Workstation>>({})

	const headers = computed(() => {
		// setup as a computed property to allow Frappe to set the CSRF token
		return {
			'Content-Type': 'application/json',
			'X-Frappe-CSRF-Token': frappe.csrf_token,
		}
	})

	watch(route, async () => {
		if (route.meta.view === 'list' && config.value.listview.includes(route.meta.doctype)) {
			context.value = { listview: route.meta.doctype }
		} else if (route.meta.view === 'form' && config.value.frm.includes(route.meta.doctype)) {
			context.value = { frm: route.meta.doctype }
		}

		form.value = {}
		if (route.meta.view === 'form' && config.value.frm.includes(route.meta.doctype)) {
			form.value = await getOne<JobCard | WorkOrder | Workstation>(route.meta.doctype, route.params.orderId.toString())
		}
	})

	const init = async () => {
		await setConfig()
	}

	const setConfig = async () => {
		if (!Object.keys(config.value).length) {
			config.value = await frappe.xcall('beam.beam.scan.config.get_scan_doctypes')
		}
	}

	const formatUrl = (url: string, params?: Record<string, any>) => {
		let fragment: string
		if (params) {
			const query = new URLSearchParams(params)
			fragment = `${url}?${query.toString()}`
		} else {
			fragment = url
		}
		return fragment
	}

	const get = async (url: string, params?: Record<string, any>) => {
		const fragment = formatUrl(url, params)
		const formattedUrl = new URL(fragment, window.location.origin)
		return await fetch(formattedUrl, {
			method: 'GET',
			headers: headers.value,
		})
	}

	const post = async (url: string, data: Record<string, any>) => {
		const formattedUrl = new URL(url, window.location.origin)
		return await fetch(formattedUrl, {
			method: 'POST',
			headers: headers.value,
			body: JSON.stringify(data),
		})
	}

	const put = async (url: string, data: Record<string, any>) => {
		const formattedUrl = new URL(url, window.location.origin)
		return await fetch(formattedUrl, {
			method: 'PUT',
			headers: headers.value,
			body: JSON.stringify(data),
		})
	}

	const getOne = async <T>(doctype: string, name: string) => {
		const url = `/api/resource/${doctype}/${name}`
		const response = await get(url)
		const { data }: { data: T } = await response.json()
		return data
	}

	const getAll = async <T>(doctype: string, params?: Record<string, any>) => {
		const url = `/api/resource/${doctype}`
		const response = await get(url, params)
		const { data }: { data: T } = await response.json()
		return data
	}

	const getDemand = async (params?: Record<string, any>) => {
		// automatically fetch all pages of demand data based on parameters
		const demandUrl = '/api/method/beam.beam.demand.demand.get_demand'
		const url = formatUrl(demandUrl, params)
		return await getPaginated(url)
	}

	// ref: https://observablehq.com/@xari/paginated_fetch
	const getPaginated = async (url: string, page: number = 1, previousResponse: any[] = []) => {
		const pageFragment = `${url}&page=${page}`
		const formattedUrl = new URL(pageFragment, window.location.origin)
		const response = await fetch(formattedUrl)
		const data = await response.json()

		const combinedResponse = [...previousResponse, ...data.message]
		if (data.message.length !== 0) {
			page++
			return await getPaginated(url, page, combinedResponse)
		}

		return { data: combinedResponse }
	}

	const scan = async (barcode: string, qty: number): Promise<(FormContext | ListContext)[]> => {
		try {
			return await frappe.xcall('beam.beam.scan.scan', {
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
		const response = await post(url, body)
		const { data, exception }: { data: T; exception: string } = await response.json()
		alert(response.ok ? 'Document created' : exception)
		return { data, exception, response }
	}

	const save = async <T>(doctype: string, name: string, body: Partial<T>) => {
		const url = `/api/resource/${doctype}/${name}`
		const response = await post(url, body)
		const { data, exception }: { data: T; exception: string } = await response.json()
		alert(response.ok ? 'Document updated' : exception)
		return { data, exception, response }
	}

	const submit = async <T>(doctype: string, name: string) => {
		const url = `/api/resource/${doctype}/${name}`
		const response = await put(url, { docstatus: 1 })
		const { data, exception }: { data: T; exception: string } = await response.json()
		alert(response.ok ? 'Document status changed to Submitted' : exception)
		return { data, exception, response }
	}

	const cancel = async <T>(doctype: string, name: string) => {
		const url = `/api/resource/${doctype}/${name}`
		const response = await put(url, { docstatus: 2 })
		const { data, exception }: { data: T; exception: string } = await response.json()
		alert(response.ok ? 'Document status changed to Cancelled' : exception)
		return { data, exception, response }
	}

	const getMappedStockEntry = async (data: Record<string, any>) => {
		const url = '/api/method/erpnext.manufacturing.doctype.work_order.work_order.make_stock_entry'
		const response = await post(url, data)
		const { message }: { message: StockEntry } = await response.json()
		if (!message) {
			alert('Error: Could not map Work Order to Stock Entry')
			return
		}
		return message
	}

	return {
		// state
		config,
		context,
		form,

		// getters
		headers,

		// store actions
		init,

		// http actions
		get,
		post,
		put,

		// document workflow actions
		cancel,
		insert,
		save,
		submit,

		// other api actions
		getAll,
		getDemand,
		getMappedStockEntry,
		getOne,
		getPaginated,
		scan,
	}
})
