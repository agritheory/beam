// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import { defineStore } from 'pinia'
import { type RouteLocationNormalized, useRoute } from 'vue-router'

import { useBeamStore } from '@/stores/beam.js'

export const useInitStore = defineStore('init', () => {
	const route = useRoute()
	const store = useBeamStore()

	const init = async (currentRoute?: RouteLocationNormalized) => {
		const resolvedRoute = currentRoute || route

		await store.getScanDoctypes()
		await store.setForm(resolvedRoute)
		await store.setMappedDoc(resolvedRoute)
		await store.setScanContext(resolvedRoute)
		await store.setWarehouses()

		// only check store actions to control toggling dirty state (vs. all state mutations);
		store.$onAction(({ name, after }) => {
			// 15 Nov '24: only scan actions affect the document's dirty state
			if (name === 'scan') {
				after(() => {
					const id = resolvedRoute.params.id || resolvedRoute.query.id
					const doc = store.cache.mappers[id]
					if (doc) {
						store.$patch(() => {
							doc.dirty = true
						})
					}
				})
			}
		})
	}

	return { init }
})
