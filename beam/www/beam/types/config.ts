export type AppList = {
	[app: string]: AppConfig
}

export type AppConfig = {
	idx?: number
	is_repo?: boolean
	required?: string[]
	version?: string
	resolution?: {
		commit_hash?: string
		branch?: string
	}
}

export type HookRoute = {
	path: string
	name: string
	component: string
	meta: { requiresAuth: boolean; doctype: string; view: 'list' | 'form' }
}

export type HookConfig = {
	components?: Record<string, string>
	file?: string
	routes?: HookRoute[]
}
