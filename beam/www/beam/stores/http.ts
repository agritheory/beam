// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import { defineStore } from 'pinia'

import { handleErrors } from '@/utils/error.js'

declare const frappe: {
	csrf_token?: string
}

function csrfToken(): string {
	if (typeof frappe !== 'undefined' && frappe.csrf_token) {
		return frappe.csrf_token
	}
	if (typeof window !== 'undefined' && (window as { csrf_token?: string }).csrf_token) {
		return (window as { csrf_token?: string }).csrf_token!
	}
	return ''
}

export const useHttpStore = defineStore('http', () => {
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
				'X-Frappe-CSRF-Token': csrfToken(),
			},
		})
	}

	const post = async (url: string, data: Record<string, any>) => {
		const formattedUrl = new URL(url, window.location.origin)
		return await fetch(formattedUrl, {
			method: 'POST',
			headers: {
				'Content-Type': 'application/json',
				'X-Frappe-CSRF-Token': csrfToken(),
			},
			body: JSON.stringify(data),
		})
	}

	const put = async (url: string, data: Record<string, any>) => {
		const formattedUrl = new URL(url, window.location.origin)
		return await fetch(formattedUrl, {
			method: 'PUT',
			headers: {
				'Content-Type': 'application/json',
				'X-Frappe-CSRF-Token': csrfToken(),
			},
			body: JSON.stringify(data),
		})
	}

	const callMethod = async <T>(method: string, args: Record<string, unknown> = {}): Promise<T> => {
		const url = `/api/method/${method}`
		const response = await post(url, args)
		if (!response.ok) {
			await handleErrors(response)
			throw new Error(method)
		}
		const { message }: { message: T } = await response.json()
		return message
	}

	return {
		// http actions
		get,
		post,
		put,
		callMethod,
	}
})
