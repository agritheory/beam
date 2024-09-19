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

import { useFetch } from '../fetch'
import type { ListViewItem, WorkOrder } from '../types'

const items = ref<ListViewItem[]>([])

onMounted(async () => {
	const { data } = await useFetch<WorkOrder[]>('/api/resource/Work Order', {
		fields: JSON.stringify(['name', 'item_name', 'qty', 'produced_qty']),
		order_by: 'creation asc',
	})

	data.forEach(row => {
		items.value.push({
			...row,
			label: row.item_name,
			count: { count: row.produced_qty, of: row.qty },
			linkComponent: 'ListAnchor',
			route: `#/work_order/${row.name}`,
		})
	})
})
</script>

<style>
@import url('@stonecrop/beam/styles');
</style>
