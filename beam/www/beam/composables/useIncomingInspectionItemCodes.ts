// Copyright (c) 2026, AgriTheory and contributors
// For license information, please see license.txt

import { ref, watch, type Ref } from 'vue'

import { useHttpStore } from '@/stores/http'

const BASE = 'beam.beam.quality_inspection'

export function useIncomingInspectionItemCodes(lineItems: Ref<{ item_code?: string }[] | undefined>) {
	const httpStore = useHttpStore()
	const itemCodes = ref<Set<string>>(new Set())

	const reload = async () => {
		const codes = [...new Set((lineItems.value || []).map(row => row.item_code).filter(Boolean) as string[])]
		if (!codes.length) {
			itemCodes.value = new Set()
			return
		}
		try {
			const message = await httpStore.callMethod<string[]>(`${BASE}.list_incoming_inspection_item_codes`, {
				item_codes: JSON.stringify(codes),
			})
			itemCodes.value = new Set(message || [])
		} catch (error) {
			console.error('list_incoming_inspection_item_codes failed', error)
			itemCodes.value = new Set()
		}
	}

	watch(lineItems, reload, { immediate: true, deep: true })

	return { itemCodes, reload }
}
