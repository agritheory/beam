<template>
	<ListView :items="items" />
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { useDataStore } from '../store'
import type { ListViewItem, WorkOrder } from '../types'

const items = ref<ListViewItem[]>([])
const store = useDataStore()

onMounted(async () => {
	const orders = await store.getAll<WorkOrder[]>('Work Order', {
		fields: JSON.stringify(['name', 'item_name', 'qty', 'produced_qty']),
		order_by: 'creation asc',
	})

	orders.forEach(row => {
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
