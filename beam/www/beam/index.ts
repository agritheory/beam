// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import { install as BeamPlugin } from '@stonecrop/beam'
import { createPinia } from 'pinia'
import { createApp, markRaw } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'
import { routes, handleHotUpdate } from 'vue-router/auto-routes'

import Beam from '@/Beam.vue'
import { useInitStore } from '@/stores/init.js'
import { BeamWindow } from '@/types/index.js'

declare const window: BeamWindow

// Create core instances
const app = createApp(Beam)
const pinia = createPinia()
const router = createRouter({
	history: createWebHashHistory(),
	routes,
})

// Install plugins first
app.use(router)
app.use(BeamPlugin)
app.use(pinia)

// Setup Pinia plugins after installation
pinia.use(({ store }) => {
	store.router = markRaw(router)
})

if (import.meta.hot) {
	handleHotUpdate(router)
}

// Now that pinia is installed, we can setup router guards
router.beforeEach(async (to, from, next) => {
	if (to.meta.requiresAuth) {
		if (window.frappe.user === 'Guest') {
			next(false)
			window.location.href = '/login?redirect-to=/beam#'
		} else {
			const store = useInitStore()
			await store.init(to)
			next()
		}
	} else {
		const store = useInitStore()
		await store.init(to)
		next()
	}
})

// Finally mount the app
app.mount('#beam')
