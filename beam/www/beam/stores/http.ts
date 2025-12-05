// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import { defineStore } from 'pinia'
import { computed } from 'vue'

declare const frappe: {
	csrf_token: string
}

export const useHttpStore = defineStore('http', () => {
	const headers = computed(() => {
		// setup as a computed property to allow Frappe to set the CSRF token
		return {
			'Content-Type': 'application/json',
			'X-Frappe-CSRF-Token': frappe.csrf_token,
		}
	})

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
			headers: {
				'Content-Type': 'application/json',
				'X-Frappe-CSRF-Token': frappe.csrf_token,
			},
		})
	}

	const post = async (url: string, data: Record<string, any>) => {
		const formattedUrl = new URL(url, window.location.origin)
		const isFrappeMethod = url.includes('/api/method/')
		
		if (isFrappeMethod) {
			// For Frappe methods, send as FormData
			const formData = new URLSearchParams()
			if (data) {
				for (const [key, value] of Object.entries(data)) {
					if (typeof value === 'object') {
						formData.append(key, JSON.stringify(value))
					} else {
						formData.append(key, String(value))
					}
				}
			}
			return await fetch(formattedUrl, {
				method: 'POST',
				headers: {
					'Accept': 'application/json',
					'X-Frappe-CSRF-Token': frappe.csrf_token,
					'X-Frappe-CMD': url.replace('/api/method/', ''),
				},
				body: formData,
			})
		} else {
			// For REST API, send as JSON
			return await fetch(formattedUrl, {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json',
					'X-Frappe-CSRF-Token': frappe.csrf_token,
				},
				body: JSON.stringify(data),
			})
		}
	}

	const put = async (url: string, data: Record<string, any>) => {
		const formattedUrl = new URL(url, window.location.origin)
		const isFrappeMethod = url.includes('/api/method/')
		
		if (isFrappeMethod) {
			// For Frappe methods, send as FormData
			const formData = new URLSearchParams()
			if (data) {
				for (const [key, value] of Object.entries(data)) {
					if (typeof value === 'object') {
						formData.append(key, JSON.stringify(value))
					} else {
						formData.append(key, String(value))
					}
				}
			}
			return await fetch(formattedUrl, {
				method: 'PUT',
				headers: {
					'Accept': 'application/json',
					'X-Frappe-CSRF-Token': frappe.csrf_token,
					'X-Frappe-CMD': url.replace('/api/method/', ''),
				},
				body: formData,
			})
		} else {
			// For REST API, send as JSON
			return await fetch(formattedUrl, {
				method: 'PUT',
				headers: {
					'Content-Type': 'application/json',
					'X-Frappe-CSRF-Token': frappe.csrf_token,
				},
				body: JSON.stringify(data),
			})
		}
	}

	return {
		// getters
		headers,

		// http actions
		get,
		post,
		put,
	}
})
