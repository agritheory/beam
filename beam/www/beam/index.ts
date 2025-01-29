// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import { install as BeamPlugin } from '@stonecrop/beam'
import { install as AformPlugin } from '@stonecrop/aform'
import { createPinia } from 'pinia'
import { createApp, markRaw } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import { routes, handleHotUpdate } from 'vue-router/auto-routes'

import Beam from '@/Beam.vue'
import { useInitStore } from '@/stores/init.js'
import { BeamWindow } from '@/types/index.js'

declare const window: BeamWindow

const router = createRouter({
	history: createWebHashHistory(),
	routes,
})

if (import.meta.hot) {
	handleHotUpdate(router)
}

router.beforeEach(async (to, from, next) => {
	if (to.meta.requiresAuth) {
		if (window.frappe.user === 'Guest') {
			next(false)
			// TODO: 6 Sep, 2024: tried redirecting to intended path, but Frappe
			// ignores everything after the hash
			window.location.href = '/login?redirect-to=/beam#'
		} else {
			const store = useInitStore()
			await store.init(to)
			next()
		}
	} else {
		// assuming user is logged in and authenticated for all Beam views
		const store = useInitStore()
		await store.init(to)
		next()
	}
})

const pinia = createPinia()
pinia.use(({ store }) => {
	store.router = markRaw(router)
})

const app = createApp(Beam)
app.use(router)
app.use(BeamPlugin)
app.use(AformPlugin)
app.use(pinia)
app.mount('#beam')
