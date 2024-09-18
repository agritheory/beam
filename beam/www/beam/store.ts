// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import { defineStore } from 'pinia'

import { useFetch } from './fetch.js'
import { FormContext, ListContext, ParentDoctype, ScanConfig, ScanContext } from './types/index.js'

declare const frappe: any

export const useDataStore = defineStore('form', {
	state: () => ({
		config: {} as ScanConfig,
		form: {} as ParentDoctype,
	}),

	getters: {
		context(state): ScanContext {
			const route = this.router.currentRoute.value
			if (route.meta.view === 'list' && state.config.listview.includes(route.meta.doctype)) {
				return { listview: route.meta.doctype }
			} else if (route.meta.view === 'form' && state.config.frm.includes(route.meta.doctype)) {
				return { frm: route.meta.doctype }
			}
		},
	},

	actions: {
		async initConfig() {
			if (!Object.keys(this.config).length) {
				this.config = await frappe.xcall('beam.beam.scan.config.get_scan_doctypes')
			}
		},

		async setFormData() {
			this.form = {}
			const route = this.router.currentRoute.value
			if (route.meta.view === 'form' && this.config.frm.includes(route.meta.doctype)) {
				this.form = await this.getDoc(route.meta.doctype, route.params.orderId.toString())
			}
		},

		async getDoc(doctype: string, name: string) {
			const { data } = await useFetch<ParentDoctype>(`/api/resource/${doctype}/${name}`)
			return data
		},

		async scan(barcode: string, qty: number): Promise<(FormContext | ListContext)[]> {
			try {
				return await frappe.xcall('beam.beam.scan.scan', {
					barcode,
					current_qty: qty,
					context: this.context,
				})
			} catch (error) {
				// TODO: handle API error
				console.error(error)
			}

			return []
		},

		async save() {
			return await frappe.xcall('frappe.desk.form.save.savedocs', {
				action: 'Save',
				doc: this.form,
			})
		},
	},
})
