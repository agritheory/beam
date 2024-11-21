<template>
	<Navbar>
		<template #title>
			<h1 class="nav-title">Manufacture</h1>
		</template>
		<template #navbaraction>
			<RouterLink :to="{ name: 'home' }">Home</RouterLink>
		</template>
	</Navbar>
	<ListView :items="items" />
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { useBeamStore } from '@/stores/beam'
import type { ListViewItem, WorkOrder } from '@/types'

declare const frappe: any

const items = ref<ListViewItem[]>([])
const store = useBeamStore()

onMounted(async () => {
	const orders = await store.getAll<WorkOrder[]>('Work Order', {
		fields: JSON.stringify(['name', 'item_name', 'qty', 'produced_qty', 'planned_start_date']),
		order_by: 'creation asc',
	})

	orders.forEach(row => {
		const plannedDate = new Date(row.planned_start_date)
		let formattedDate = ''
		if (!isNaN(plannedDate.getTime())) {
			formattedDate = plannedDate.toLocaleString(frappe.boot.time_zone, {
				year: 'numeric',
				month: 'numeric',
				day: 'numeric',
				hour: '2-digit',
				minute: '2-digit',
			})
		}

		items.value.push({
			...row,
			label: `${row.name} - ${row.item_name}`,
			description: `Start: ${formattedDate}`,
			count: { count: row.produced_qty, of: row.qty },
			linkComponent: 'ListAnchor',
			route: `#/work_order/${row.name}`,
		})
	})
})
</script>
