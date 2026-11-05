// Copyright (c) 2026, AgriTheory and contributors
// For license information, please see license.txt

import { ref, watch, type Ref } from 'vue'

import { useInspectionStore } from '@/stores/inspection'
import type { LineInspection } from '@/types/inspection'
import { indexInspectionsByRow } from '@/utils/inspectionList'

type LineItem = Record<string, unknown>

export function useLineInspections(
	doctype: Ref<string | undefined>,
	docname: Ref<string | undefined>,
	lineItems?: Ref<LineItem[] | undefined>
) {
	const inspectionStore = useInspectionStore()
	const byRow = ref<Record<string, LineInspection>>({})

	const reload = async () => {
		if (!doctype.value) {
			byRow.value = {}
			return
		}

		try {
			if (docname.value && !docname.value.startsWith('new-')) {
				const lines = await inspectionStore.lines(doctype.value, docname.value)
				byRow.value = indexInspectionsByRow(lines)
				return
			}

			const items = lineItems?.value
			if (!items?.length) {
				byRow.value = {}
				return
			}

			const lines = await inspectionStore.previewLines(doctype.value, items)
			byRow.value = indexInspectionsByRow(lines)
		} catch (error) {
			console.error('line inspection reload failed', error)
			byRow.value = {}
		}
	}

	watch([doctype, docname, () => lineItems?.value], reload, { immediate: true, deep: true })

	return { byRow, reload }
}
