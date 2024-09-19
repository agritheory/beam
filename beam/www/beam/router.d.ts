// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import 'vue-router'

declare module 'vue-router' {
	interface RouteMeta {
		doctype: string
		requiresAuth: boolean
		view: 'list' | 'form'
	}
}

export {}
