<template>
	<Navbar>
		<template #title>
			<h1>Manufacture</h1>
		</template>
		<template #navbaraction>
			<RouterLink :to="{ name: 'home' }">Home</RouterLink>
		</template>
	</Navbar>
	<ListView :items="items" />
</template>

<script setup lang="ts">
import type { ListViewItem } from '@stonecrop/beam'
import { onMounted, ref } from 'vue'

import { useBeamStore } from '@/stores/beam'
import type { WorkOrder } from '@/types'

const items = ref<ListViewItem[]>([])
const store = useBeamStore()

onMounted(async () => {
	const orders = await store.getAll<WorkOrder[]>('Work Order', {
		fields: JSON.stringify(['name', 'item_name', 'qty', 'produced_qty', 'planned_start_date']),
		order_by: 'creation asc',
	})

	const dates: string[] = []
	orders.forEach(row => {
		const plannedDate = new Date(row.planned_start_date)
		const formattedDate = store.formatDate(plannedDate)

		// add day-divider config when date changes
		if (!dates.includes(plannedDate.toDateString())) {
			dates.push(plannedDate.toDateString())
			items.value.push({
				date: plannedDate.toISOString(),
				linkComponent: 'BeamDayDivider',
			})
		}

		items.value.push({
			...row,
			label: `${row.name} - ${row.item_name}`,
			description: formattedDate ? `Start: ${formattedDate}` : '',
			count: { count: row.produced_qty, of: row.qty },
			linkComponent: 'ListAnchor',
			route: `#/work_order/${row.name}`,
		})
	})
})
</script>
