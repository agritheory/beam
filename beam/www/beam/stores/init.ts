// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import { defineStore } from 'pinia'
import { type RouteLocationNormalized, useRoute } from 'vue-router'

import { useBeamStore } from '@/stores/beam.js'

export const useInitStore = defineStore('init', () => {
	const route = useRoute()
	const store = useBeamStore()

	const init = async (currentRoute?: RouteLocationNormalized) => {
		await store.getScanDoctypes()
		await store.setForm(currentRoute || route)
		await store.setScanContext(currentRoute || route)

		// only check store actions to control toggling dirty state (vs. all state mutations);
		// also globally ignore certain actions (store init, background fetching, etc.)
		const ignoredActions = ['getMappedStockEntry', 'getScanDoctypes', 'setForm', 'setScanContext']
		store.$onAction(({ name, after }) => {
			after(() => {
				if (!ignoredActions.includes(name)) {
					const id = route.params.id || route.query.id
					const doc = store.cache.mappers[id]
					if (doc) {
						store.$patch(() => {
							doc.dirty = true
						})
					}
				}
			})
		})
	}

	return { init }
})
