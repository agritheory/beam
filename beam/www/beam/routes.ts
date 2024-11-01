// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import type { RouteRecordRaw } from 'vue-router'
import Home from './pages/Home.vue'

const routes: RouteRecordRaw[] = [
	{
		path: '/',
		name: 'home',
		component: Home,
		meta: { requiresAuth: true, doctype: null, view: 'list' },
	},
]

export default routes
