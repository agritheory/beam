<template>
	<!-- navigation section -->
	<Navbar>
		<template #title>
			<h1>Demand</h1>
		</template>
		<template #navbaraction>
			<RouterLink :to="{ name: 'home' }">Home</RouterLink>
		</template>
	</Navbar>

	<!-- scan section -->
	<ScanOutput v-if="store.scanner.config.show_scan_output" />

	<!-- filters section -->
	<DemandFilters @filter="filterDemand" />

	<!-- body section -->
	<ListView :items="demandList" :key="listKey" />
</template>

<script setup lang="ts">
import type { ListViewItem } from '@stonecrop/beam'
import { useInfiniteScroll } from '@vueuse/core'
import { ref } from 'vue'

import ScanOutput from '@/components/ScanOutput.vue'
import DemandFilters from '@/components/DemandFilters.vue'
import { useBeamStore } from '@/stores/beam'
import type { Demand, DemandFilter } from '@/types'

declare const frappe: any

const store = useBeamStore()
const dates = ref<(string | null)[]>([])
const demand = ref<Demand[]>([])
const demandList = ref<ListViewItem[]>([])
const filters = ref<Record<string, any>>({})
const canLoadMore = ref(true)
const page = ref(1)
const listKey = ref(0)

const getDemand = async () => {
	const { data } = await store.getDemand({
		...(Object.keys(filters.value).length && { filters: JSON.stringify(filters.value) }),
		page: page.value,
	})

	if (!data || data.length === 0) {
		canLoadMore.value = false
	} else {
		demand.value = [...demand.value, ...data]
		page.value++
	}

	setDemand()
	listKey.value++
}

const setDemand = () => {
	dates.value = []
	demandList.value = []

	// TODO: move this to the server
	for (const row of demand.value) {
		// add day-divider config when date changes
		addDivider(row.allocated_date)

		demandList.value.push({
			label: `${row.item_code} from ${row.item_warehouse}`,
			linkComponent: 'ListAnchor',
			route: `#/${frappe.scrub(row.doctype)}/${row.parent}`,
			description: `
					[${row.parent}]
					Production Item: ${row.production_item}
					BOM No: ${row.bom_no}
				`.trim(),
			count: {
				count: +row.allocated_qty.toFixed(2),
				of: +row.total_required_qty.toFixed(2),
			},
		})
	}
}

const addDivider = (date: string | null) => {
	if (date) {
		const scheduledDate = new Date(date)
		if (!dates.value.includes(scheduledDate.toDateString())) {
			dates.value.push(scheduledDate.toDateString())
			demandList.value.push({
				date: scheduledDate.toISOString(),
				linkComponent: 'BeamDayDivider',
			})
		}
	} else {
		if (!dates.value.includes(null)) {
			dates.value.push(null)
			demandList.value.push({
				date: 'No Date Set',
				linkComponent: 'BeamDayDivider',
			})
		}
	}
}

const resetDemand = () => {
	page.value = 1
	dates.value = []
	demand.value = []
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

const filterDemand = async (demandFilters: DemandFilter) => {
	resetDemand()
	setFilters(demandFilters)
	await getDemand()
}

useInfiniteScroll(window, getDemand, { canLoadMore: () => canLoadMore.value })
</script>
