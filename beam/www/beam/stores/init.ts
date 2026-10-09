// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import { defineStore } from 'pinia'
import { type RouteLocationNormalized, useRoute } from 'vue-router'

import { useBeamStore } from '@/stores/beam.js'
import { useScanStore } from '@/stores/scan.js'

function markMappedDocDirty(store: ReturnType<typeof useBeamStore>, route: RouteLocationNormalized) {
	const id = route.params.id || route.query.id
	if (!id) return
	const doc = store.cache.mappers[id.toString()]
	if (!doc) return
	store.$patch(() => {
		doc.dirty = true
	})
}

export const useInitStore = defineStore('init', () => {
	const route = useRoute()
	const store = useBeamStore()

	const init = async (currentRoute?: RouteLocationNormalized) => {
		const resolvedRoute = currentRoute || route

		await store.getScanDoctypes()
		await store.setCurrentEmployee()
		await store.setForm(resolvedRoute)
		await store.setMappedDoc(resolvedRoute)
		await store.setScanContext(resolvedRoute)
		console.log('init: setting warehouses')
		await store.setWarehouses()

		const scanStore = useScanStore()

		// only check store actions to control toggling dirty state (vs. all state mutations);
		store.$onAction(({ name, after }) => {
			// 15 Nov '24: only scan actions affect the document's dirty state
			if (name === 'scan') {
				after(() => markMappedDocDirty(store, store.router.currentRoute.value))
			}
		})
		scanStore.$onAction(({ name, after }) => {
			if (name === 'scan') {
				after(() => markMappedDocDirty(store, store.router.currentRoute.value))
			}
		})
	}

	return { init }
})
