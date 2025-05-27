<template>
	<!-- navigation section -->
	<Navbar>
		<template #title>
			<h1>Ship</h1>
		</template>
		<template #navbaraction>
			<RouterLink :to="{ name: 'home' }">Home</RouterLink>
		</template>
	</Navbar>

	<!-- scan section -->
	<ScanOutput v-show="store.scanner.config.show_scan_output" />

	<!-- filters section -->
	<DemandFilters @filter="filterShipments" />

	<!-- body section -->
	<ListView :items="shipList" :key="listKey" />
</template>

<script setup lang="ts">
import type { ListViewItem } from '@stonecrop/beam'
import { useInfiniteScroll } from '@vueuse/core'
import { ref } from 'vue'

import DemandFilters from '@/components/DemandFilters.vue'
import ScanOutput from '@/components/ScanOutput.vue'
import { useBeamStore } from '@/stores/beam'
import type { Demand, DemandFilter } from '@/types'

const store = useBeamStore()
const dates = ref<(string | null)[]>([])
const ship = ref<Demand[]>([])
const shipList = ref<ListViewItem[]>([])
const filters = ref<Record<string, any>>({ doctype: 'Sales Order' })
const canLoadMore = ref(true)
const page = ref(1)
const listKey = ref(0)

const getShipments = async () => {
	const { data } = await store.getDemand({
		...(Object.keys(filters.value).length && { filters: JSON.stringify(filters.value) }),
		page: page.value,
	})

	if (!data || data.length === 0) {
		canLoadMore.value = false
	} else {
		ship.value = [...ship.value, ...data]
		page.value++
	}

	setShipments()
	listKey.value++
}

const setShipments = () => {
	dates.value = []
	shipList.value = []

	// TODO: move this to the server
	for (const row of ship.value) {
		// add day-divider config when date changes
		addDivider(row.delivery_date)

		shipList.value.push({
			count: { count: row.allocated_qty, of: row.total_required_qty },
			label: `${row.doctype} - ${row.parent}`,
			linkComponent: 'ListAnchor',
			description: `
					Item: ${row.item_code}
					Warehouse: ${row.warehouse}
					${row.customer ?? `Customer: ${row.customer}`}
				`.trim(),
			route: `#/delivery-note?id=${row.parent}`,
		})
	}
}

const addDivider = (date: string | null) => {
	if (date) {
		const scheduledDate = new Date(date)
		if (!dates.value.includes(scheduledDate.toDateString())) {
			dates.value.push(scheduledDate.toDateString())
			shipList.value.push({
				date: scheduledDate.toISOString(),
				linkComponent: 'BeamDayDivider',
			})
		}
	} else {
		if (!dates.value.includes(null)) {
			dates.value.push(null)
			shipList.value.push({
				date: 'No Date Set',
				linkComponent: 'BeamDayDivider',
			})
		}
	}
}

const resetShipments = () => {
	page.value = 1
	ship.value = []
	canLoadMore.value = true
}

const setFilters = (demandFilters: DemandFilter) => {
	if (demandFilters.status) {
		filters.value.status = demandFilters.status
	} else {
		delete filters.value.status
	}
	if (demandFilters.date) {
		filters.value.delivery_date = demandFilters.date
	} else {
		delete filters.value.delivery_date
	}
	if (demandFilters.user) {
		filters.value.assigned = demandFilters.user
	} else {
		delete filters.value.assigned
	}
}

const filterShipments = async (demandFilters: DemandFilter) => {
	resetShipments()
	setFilters(demandFilters)
	await getShipments()
}

useInfiniteScroll(window, getShipments, { canLoadMore: () => canLoadMore.value })
</script>
