<template>
	<Navbar @click="handlePrimaryAction">
		<template #title>
			<h1 class="nav-title">Manufacture</h1>
		</template>
		<template #navbaraction>Home</template>
	</Navbar>
	<ListView :items="items" />
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { useDataStore } from '@/store'
import type { ListViewItem, WorkOrder } from '@/types'

const items = ref<ListViewItem[]>([])
const store = useDataStore()

onMounted(async () => {
	const orders = await store.getAll<WorkOrder[]>('Work Order', {
		fields: JSON.stringify(['name', 'item_name', 'qty', 'produced_qty', 'planned_start_date']),
		order_by: 'creation asc',
	})

	orders.forEach(row => {
		const order = row.name?.split('-').pop()
		const plannedDate = new Date(row.planned_start_date)
		let formattedDate = ''
		if (!isNaN(plannedDate.getTime())) formattedDate = plannedDate.toISOString().split('T')[0]

		items.value.push({
			...row,
			label: `${order} - ${row.item_name}`,
			description: formattedDate,
			count: { count: row.produced_qty, of: row.qty },
			linkComponent: 'ListAnchor',
			route: `#/work_order/${row.name}`,
		})
	})
})

const handlePrimaryAction = () => {
	console.log('handle primary action')
}
</script>

<style>
@import url('@stonecrop/beam/styles');
</style>
