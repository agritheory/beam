// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import { install as BeamPlugin } from '@stonecrop/beam'
import { createPinia } from 'pinia'
import { createApp } from 'vue'
import { createRouter, createWebHashHistory } from 'vue-router'

import Beam from './Beam.vue'
import { makeServer } from './mocks/mirage'
import routes from './routes'

if (import.meta.env.DEV) {
	makeServer()
}

interface FrappeWindow extends Window {
	frappe: any
}
declare const window: FrappeWindow

const router = createRouter({
	history: createWebHashHistory(),
	routes,
})

router.beforeEach((to, from, next) => {
	if (!window.frappe) {
		// dev environment; simply proceed with path
		next()
	} else {
		if (to.meta.requiresAuth) {
			if (window.frappe.user === 'Guest') {
				next(false)
				// TODO: 6 Sep, 2024: tried redirecting to intended path, but Frappe
				// ignores everything after the hash
				window.location.href = '/login?redirect-to=/beam#'
			} else {
				next()
			}
		} else {
			next()
		}
	}
})

const pinia = createPinia()
const app = createApp(Beam)
app.use(router)
app.use(BeamPlugin)
app.use(pinia)
app.mount('#beam')
