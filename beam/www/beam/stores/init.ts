// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import { defineStore, storeToRefs } from 'pinia'
import { watch } from 'vue'
import { type RouteLocationNormalized, useRoute } from 'vue-router'

import { useBeamStore } from '@/stores/beam.js'

export const useInitStore = defineStore('init', () => {
	const route = useRoute()
	const store = useBeamStore()

	watch(route, async () => await init())

	const init = async (currentRoute?: RouteLocationNormalized) => {
		await store.getScanDoctypes()
		await store.setForm(currentRoute || route)
		await store.setScanContext(currentRoute || route)
	}

	return { init }
})
