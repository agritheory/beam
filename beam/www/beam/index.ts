// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import { install as BeamPlugin } from '@stonecrop/beam'
import { createPinia } from 'pinia'
import { createApp } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'

import Beam from './Beam.vue'
import routes from './routes'
import { useDataStore } from './store'

const router = createRouter({
	history: createWebHashHistory(),
	routes,
})

router.beforeEach(async (to, from, next) => {
	if (to.meta.requiresAuth) {
		if (window.frappe.user === 'Guest') {
			next(false)
			// TODO: 6 Sep, 2024: tried redirecting to intended path, but Frappe
			// ignores everything after the hash
			window.location.href = '/login?redirect-to=/beam#'
		} else {
			const store = useDataStore()
			await store.init(to)
			next()
		}
	} else {
		// assuming user is logged in and authenticated for all Beam views
		const store = useDataStore()
		await store.init(to)
		next()
	}
})

const pinia = createPinia()
const app = createApp(Beam)
app.use(router)
app.use(BeamPlugin)
app.use(pinia)
app.mount('#beam')
