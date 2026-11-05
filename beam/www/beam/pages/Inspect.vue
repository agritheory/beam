<template>
	<Navbar>
		<template #title>
			<h1>Inspect</h1>
		</template>
		<template #navbaraction>
			<RouterLink :to="{ name: 'home' }">Home</RouterLink>
		</template>
	</Navbar>

	<DemandFilters @filter="filterAwaiting" />

	<ListView :items="awaitingList" />
</template>

<script setup lang="ts">
import type { ListViewItem } from '@/types/stonecrop.js'
import { onMounted, ref } from 'vue'
import { useInfiniteScroll } from '@vueuse/core'

import DemandFilters from '@/components/DemandFilters.vue'
import { useInspectionStore } from '@/stores/inspection'
import type { DemandFilter } from '@/types'
import type { AwaitingLine } from '@/types/inspection'

const inspectionStore = useInspectionStore()
const awaitingList = ref<ListViewItem[]>([])
const filters = ref<DemandFilter>({})
const page = ref(1)
const canLoadMore = ref(true)
const loading = ref(false)
const dates = ref<(string | null)[]>([])

const appendRows = (rows: AwaitingLine[], fromIndex: number) => {
	for (const row of rows.slice(fromIndex)) {
		const dateKey = row.schedule_date || null
		if (!dates.value.includes(dateKey)) {
			dates.value.push(dateKey)
			awaitingList.value.push({
				barcode: `divider:${dateKey ?? 'none'}`,
				date: dateKey || 'No Date Set',
				linkComponent: 'BeamDayDivider',
			})
		}
		const kindLabel = row.kind === 'hold' ? ' (held)' : ''
		awaitingList.value.push({
			barcode: `${row.reference_name}:${row.row}`,
			label: `${row.item_code}${kindLabel}`,
			description: `${row.reference_type} ${row.reference_name}`,
			linkComponent: 'ListAnchor',
			route: `${inspectionStore.inspectionHash(
				row.reference_type,
				row.reference_name,
				row.row,
				row.state
			)}&from=${encodeURIComponent('#/inspect')}`,
		})
	}
}

const loadAwaiting = async () => {
	if (loading.value || !canLoadMore.value) return
	loading.value = true
	try {
		const startLen = awaitingList.value.length
		const rows = await inspectionStore.awaiting(filters.value, page.value)
		if (!rows.length) {
			canLoadMore.value = false
			return
		}
		appendRows(rows, 0)
		page.value++
		if (rows.length < 20) canLoadMore.value = false
	} finally {
		loading.value = false
	}
}

const reset = () => {
	page.value = 1
	canLoadMore.value = true
	awaitingList.value = []
	dates.value = []
}

const filterAwaiting = async (demandFilters: DemandFilter) => {
	filters.value = demandFilters
	reset()
	await loadAwaiting()
}

useInfiniteScroll(window, loadAwaiting, { canLoadMore: () => canLoadMore.value })

onMounted(() => {
	loadAwaiting()
})
</script>
