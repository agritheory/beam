/// <reference types="vite/client" />

declare global {
	const frappe: {
		csrf_token?: string
		call: (opts: any) => Promise<any>
	}

	interface Window {
		csrf_token?: string
	}
}

export {}
