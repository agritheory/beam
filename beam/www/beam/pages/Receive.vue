<template>
	<!-- navigation section -->
	<Navbar>
		<template #title>
			<h1>Receive</h1>
		</template>
		<template #navbaraction>
			<RouterLink :to="{ name: 'home' }">Home</RouterLink>
		</template>
	</Navbar>

	<!-- scan section -->
	<ScanOutput v-if="store.scanner.config.show_scan_output" />

	<!-- filters section -->
	<DemandFilters @filter="filterReceive" />

	<!-- body section -->
	<ListView :items="receiveList" :key="listKey" />
</template>

<script setup lang="ts">
import type { ListViewItem } from '@stonecrop/beam'
import { useInfiniteScroll } from '@vueuse/core'
import { ref } from 'vue'

import ScanOutput from '@/components/ScanOutput.vue'
import DemandFilters from '@/components/DemandFilters.vue'
import { useBeamStore } from '@/stores/beam'
import type { DemandFilter, Receive } from '@/types'

const store = useBeamStore()
const dates = ref<(string | null)[]>([])
const receive = ref<Receive[]>([])
const receiveList = ref<ListViewItem[]>([])
const filters = ref<Record<string, any>>({})
const canLoadMore = ref(true)
const page = ref(1)
const listKey = ref(0)

const getReceive = async () => {
	const { data } = await store.getReceiving({
		...(Object.keys(filters.value).length && { filters: JSON.stringify(filters.value) }),
		page: page.value,
	})

	if (!data || data.length === 0) {
		canLoadMore.value = false
	} else {
		receive.value = [...receive.value, ...data]
		page.value++
	}

	setReceive()
	listKey.value++
}

const setReceive = () => {
	dates.value = []
	receiveList.value = []

	// TODO: move this to the server
	for (const row of receive.value) {
		// add day-divider config when date changes
		addDivider(row.schedule_date)

		receiveList.value.push({
			count: { count: row.received_qty, of: row.stock_qty },
			label: `${row.item_code} from ${row.warehouse}`,
			linkComponent: 'ListAnchor',
			description: `
					[${row.parent}]
					Warehouse: ${row.warehouse}
					Supplier: ${row.supplier}
				`.trim(),
			route: `#/purchase_order/${row.parent || 'new-purchase-order'}`,
		})
	}
}

const addDivider = (date: string | null) => {
	if (date) {
		const scheduledDate = new Date(date)
		if (!dates.value.includes(scheduledDate.toDateString())) {
			dates.value.push(scheduledDate.toDateString())
			receiveList.value.push({
				date: scheduledDate.toISOString(),
				linkComponent: 'BeamDayDivider',
			})
		}
	} else {
		if (!dates.value.includes(null)) {
			dates.value.push(null)
			receiveList.value.push({
				date: 'No Date Set',
				linkComponent: 'BeamDayDivider',
			})
		}
	}
}

const resetReceive = () => {
	page.value = 1
	receive.value = []
	canLoadMore.value = true
}

const setFilters = (demandFilters: DemandFilter) => {
	if (demandFilters.status) {
		filters.value.status = demandFilters.status
	} else {
		delete filters.value.status
	}
	if (demandFilters.date) {
		filters.value.schedule_date = demandFilters.date
	} else {
		delete filters.value.schedule_date
	}
	if (demandFilters.user) {
		filters.value.assigned = demandFilters.user
	} else {
		delete filters.value.assigned
	}
}

const filterReceive = async (demandFilters: DemandFilter) => {
	resetReceive()
	setFilters(demandFilters)
	await getReceive()
}

useInfiniteScroll(window, getReceive, { canLoadMore: () => canLoadMore.value })
</script>

<style>
.beam_list-text label,
.beam_list-text p {
	white-space: pre-line !important;
}
</style>
