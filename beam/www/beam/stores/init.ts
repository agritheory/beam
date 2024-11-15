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
		await store.setMappedDoc(currentRoute || route)
		await store.setScanContext(currentRoute || route)

		// only check store actions to control toggling dirty state (vs. all state mutations);
		store.$onAction(({ name, after }) => {
			after(() => {
				const id = route.params.id || route.query.id
				const doc = store.cache.mappers[id]
				if (doc) {
					// currently only scan actions affect the document's dirty state
					if (name === 'scan') {
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
