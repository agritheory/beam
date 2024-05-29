/// <reference types="vite/client" />

interface ImportMetaEnv {
	readonly FRAPPE_DEV_MODE: boolean
}

interface ImportMeta {
	readonly env: ImportMetaEnv
}
