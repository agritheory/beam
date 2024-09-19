// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import { defineStore } from 'pinia'
import { ref, watch } from 'vue'
import { useRoute } from 'vue-router'

import type {
	FormContext,
	JobCard,
	ListContext,
	ScanConfig,
	ScanContext,
	WorkOrder,
	Workstation,
} from './types/index.js'

declare const frappe: any

export const useDataStore = defineStore('data', () => {
	const route = useRoute()

	const config = ref<ScanConfig>({})
	const context = ref<ScanContext>({})
	const form = ref<Partial<JobCard | WorkOrder | Workstation>>({})

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

	const getFetchUrl = (url: string, params?: Record<string, any>) => {
		let fragment: string
		if (params) {
			const query = new URLSearchParams(params)
			fragment = `${url}?${query.toString()}`
		} else {
			fragment = url
		}
		return fragment
	}

	const get = async <T>(url: string, params?: Record<string, any>) => {
		const fragment = getFetchUrl(url, params)
		const formattedUrl = new URL(fragment, window.location.origin)
		const response = await fetch(formattedUrl)
		const { data }: { data: T } = await response.json()
		return data
	}

	const getOne = async <T>(doctype: string, name: string) => {
		const url = `/api/resource/${doctype}/${name}`
		return await get<T>(url)
	}

	const getAll = async <T>(doctype: string, params?: Record<string, any>) => {
		const url = `/api/resource/${doctype}`
		return await get<T>(url, params)
	}

	const getDemand = async (params?: Record<string, any>) => {
		// automatically fetch all pages of demand data based on parameters
		const demandUrl = '/api/method/beam.beam.demand.demand.get_demand'
		const url = getFetchUrl(demandUrl, params)
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

	const save = async () => {
		return await frappe.xcall('frappe.desk.form.save.savedocs', {
			action: 'Save',
			doc: form.value,
		})
	}

	return {
		// state
		config,
		context,
		form,

		// actions
		get,
		getAll,
		getDemand,
		getOne,
		getFetchUrl,
		getPaginated,
		init,
		save,
		scan,
	}
})
