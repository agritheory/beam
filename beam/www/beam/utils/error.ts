import type { FrappeResponse } from '@/types/frappe.js'
import { useBeamToast } from '@/utils/toast.js'

const getFormattedErrors = (serverMessages: string) => {
	const formattedMessages: string[] = []
	const parsedMessages: string[] = JSON.parse(serverMessages)
	if (Array.isArray(parsedMessages)) {
		for (const message of parsedMessages) {
			formattedMessages.push(JSON.parse(message).message)
		}
	}
	return formattedMessages
}

const handleErrors = async (response: Response) => {
	const toast = useBeamToast()
	const { _server_messages }: FrappeResponse = await response.json()
	const errors = getFormattedErrors(_server_messages)
	for (const error of errors) {
		toast.error(error)
	}
}

export { getFormattedErrors, handleErrors }
