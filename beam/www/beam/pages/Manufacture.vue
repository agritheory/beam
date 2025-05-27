<template>
	<!-- navigation section -->
	<Navbar>
		<template #title>
			<h1>Manufacture</h1>
		</template>
		<template #navbaraction>
			<RouterLink :to="{ name: 'home' }">Home</RouterLink>
		</template>
	</Navbar>

	<!-- scan section -->
	<ScanOutput v-if="store.scanner.config.show_scan_output" />

	<!-- filters section -->
	<BeamFilter>
		<BeamFilterOption
			title="Status"
			:choices="[
				{ label: 'All', value: 'all' },
				{ label: 'Not Started', value: 'not_started' },
				{ label: 'In Process', value: 'in_process' },
				{ label: 'Completed', value: 'completed' },
			]"
			@select="filterByStatus" />
		<BeamFilterOption
			title="Start Date"
			:choices="[
				{ label: 'All', value: 'all' },
				{ label: 'Past', value: 'past' },
				{ label: 'Today', value: 'today' },
				{ label: 'Future', value: 'future' },
			]"
			@select="filterByDate" />
		<UserFilter :filter="filterByUser" />
	</BeamFilter>

	<!-- body section -->
	<ListView :items="items" :key="listKey" />
</template>

<script setup lang="ts">
import type { BeamFilterChoice, ListViewItem } from '@stonecrop/beam'
import { onMounted, ref } from 'vue'

import UserFilter from '@/components/UserFilter.vue'
import ScanOutput from '@/components/ScanOutput.vue'

import { useBeamStore } from '@/stores/beam'
import type { WorkOrder } from '@/types'

const dates = ref<(string | null)[]>([])
const filters = ref<Record<string, any>>({})
const items = ref<ListViewItem[]>([])
const orders = ref<WorkOrder[]>([])
const store = useBeamStore()
const listKey = ref(0)

onMounted(async () => {
	await getItems()
})

const getItems = async () => {
	orders.value = await store.getAll<WorkOrder>('Work Order', {
		...(Object.keys(filters.value).length && { filters: JSON.stringify(filters.value) }),
		fields: JSON.stringify(['name', 'item_name', 'qty', 'produced_qty', 'planned_start_date', 'status']),
		order_by: 'creation asc',
	})

	setItems(orders.value)
}

const setItems = (orders: WorkOrder[]) => {
	items.value = []
	dates.value = []

	orders.forEach(row => {
		// add day-divider config when date changes
		const plannedDate = new Date(row.planned_start_date)
		if (!dates.value.includes(plannedDate.toDateString())) {
			dates.value.push(plannedDate.toDateString())
			items.value.push({
				date: plannedDate.toISOString(),
				linkComponent: 'BeamDayDivider',
			})
		}

		const formattedDate = store.formatDate(plannedDate)
		items.value.push({
			...row,
			label: `${row.name} - ${row.item_name}`,
			description: formattedDate ? `Start: ${formattedDate}` : '',
			count: { count: row.produced_qty, of: row.qty },
			linkComponent: 'ListAnchor',
			route: `#/work_order/${row.name}`,
		})
	})
}

const filterByStatus = async (choice: BeamFilterChoice) => {
	switch (choice.value) {
		case 'all':
			delete filters.value.status
			break
		case 'not_started':
			filters.value.status = 'Not Started'
			break
		case 'in_process':
			filters.value.status = 'In Process'
			break
		case 'completed':
			filters.value.status = 'Completed'
			break
	}

	await getItems()
}

const filterByDate = async (choice: BeamFilterChoice) => {
	const today = new Date()
	const todayString = today.toISOString().split('T')[0]

	switch (choice.value) {
		case 'all':
			delete filters.value.planned_start_date
			break
		case 'past':
			filters.value.planned_start_date = ['<', todayString]
			break
		case 'today':
			filters.value.planned_start_date = todayString
			break
		case 'future':
			filters.value.planned_start_date = ['>', todayString]
			break
	}

	await getItems()
}

const filterByUser = async (choice: BeamFilterChoice) => {
	if (choice.value === 'all') {
		delete filters.value._assign
	} else {
		filters.value._assign = ['like', `%${choice.value}%`]
	}

	await getItems()
}
</script>
