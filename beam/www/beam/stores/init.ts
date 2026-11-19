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
	if (!doc || doc.dirty) return
	store.$patch(() => {
		doc.dirty = true
	})
}

// init() runs on every navigation. Registering these inside init() stacked a new
// listener each time, and each one $patch'd the open document after a scan.
let scanDirtyWatchRegistered = false

function registerScanDirtyWatch(store: ReturnType<typeof useBeamStore>, scanStore: ReturnType<typeof useScanStore>) {
	if (scanDirtyWatchRegistered) return

	const afterScan = () => markMappedDocDirty(store, store.router.currentRoute.value)
	store.$onAction(({ name, after }) => {
		if (name === 'scan') after(afterScan)
	})
	scanStore.$onAction(({ name, after }) => {
		if (name === 'scan') after(afterScan)
	})
	scanDirtyWatchRegistered = true
}

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

		// only scan actions toggle the document's dirty state (not every store write)
		registerScanDirtyWatch(store, useScanStore())
	}

	return { init }
})
