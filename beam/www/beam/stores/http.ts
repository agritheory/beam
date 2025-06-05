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

	return {
		// getters
		headers,

		// http actions
		get,
		post,
		put,
	}
})
