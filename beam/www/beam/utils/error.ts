// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import type { FrappeResponse } from '@/types/frappe.js'
import { useBeamToast } from '@/utils/toast.js'

const getFormattedErrors = (serverMessages?: string) => {
	const formattedMessages: string[] = []
	if (!serverMessages) return formattedMessages

	let parsedMessages: unknown
	try {
		parsedMessages = JSON.parse(serverMessages)
	} catch {
		return [serverMessages]
	}

	if (Array.isArray(parsedMessages)) {
		for (const message of parsedMessages) {
			try {
				formattedMessages.push(JSON.parse(message).message)
			} catch {
				formattedMessages.push(String(message))
			}
		}
	}
	return formattedMessages
}

const handleErrors = async (response: Response) => {
	const toast = useBeamToast()

	let serverMessages: string | undefined
	try {
		const body: FrappeResponse = await response.json()
		serverMessages = body._server_messages
	} catch {}

	const errors = getFormattedErrors(serverMessages)
	if (errors.length === 0) {
		toast.error(`Request failed (${response.status} ${response.statusText || 'error'})`)
		return
	}

	for (const error of errors) {
		toast.error(error)
	}
}

export { getFormattedErrors, handleErrors }
