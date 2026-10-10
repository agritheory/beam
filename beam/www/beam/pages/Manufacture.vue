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
		<BeamFilterOption title="Status" :choices="statusFilterChoices" @select="filterByStatus" />
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
import { computed, onMounted, ref } from 'vue'

import UserFilter from '@/components/UserFilter.vue'
import ScanOutput from '@/components/ScanOutput.vue'

import { useBeamStore } from '@/stores/beam'
import { defaultCompany } from '@/utils/company'
import { appendUomText } from '@/utils/itemListLine'
import type { WorkOrder } from '@/types'

declare const frappe: any

const dates = ref<(string | null)[]>([])
const filters = ref<Record<string, any>>({})
const items = ref<ListViewItem[]>([])
const orders = ref<WorkOrder[]>([])
const store = useBeamStore()
const listKey = ref(0)

const showDraftWorkOrders = (): boolean => {
	const company = defaultCompany()
	const settings = company ? frappe?.boot?.beam?.settings?.[company] : undefined
	return Boolean(settings?.show_draft_work_orders)
}

const statusFilterChoices = computed((): BeamFilterChoice[] => {
	const choices: BeamFilterChoice[] = [
		{ label: 'All', value: 'all' },
		{ label: 'Not Started', value: 'not_started' },
		{ label: 'In Process', value: 'in_process' },
		{ label: 'Completed', value: 'completed' },
	]
	if (showDraftWorkOrders()) {
		choices.splice(1, 0, { label: 'Draft', value: 'draft' })
	}
	return choices
})

onMounted(async () => {
	await getItems()
})

const getItems = async () => {
	const queryFilters: Record<string, unknown> = { ...filters.value }
	if (!showDraftWorkOrders()) {
		queryFilters.docstatus = 1
	}

	orders.value = await store.getAll<WorkOrder>('Work Order', {
		...(Object.keys(queryFilters).length && { filters: JSON.stringify(queryFilters) }),
		fields: JSON.stringify([
			'name',
			'item_name',
			'qty',
			'produced_qty',
			'stock_uom',
			'planned_start_date',
			'status',
			'docstatus',
		]),
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
				barcode: `divider:${plannedDate.toDateString()}`,
				date: plannedDate.toISOString(),
				linkComponent: 'BeamDayDivider',
			})
		}

		const formattedDate = store.formatDate(plannedDate)
		items.value.push({
			...row,
			barcode: row.name,
			label: `${row.name} - ${row.item_name}`,
			description: appendUomText(formattedDate ? `Start: ${formattedDate}` : '', row),
			count: {
				count: row.produced_qty,
				of: row.qty,
			},
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
		case 'draft':
			filters.value.status = 'Draft'
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
