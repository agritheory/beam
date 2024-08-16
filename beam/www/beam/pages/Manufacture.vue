<template>
	<ListView :items="items" />
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import type { ListViewItem, WorkOrder } from '../types'

const items = ref<ListViewItem[]>([])

onMounted(async () => {
	const params = new URLSearchParams({
		fields: JSON.stringify(['name', 'item_name', 'qty', 'produced_qty']),
		order_by: 'creation asc',
	})

	const url = new URL(`/api/resource/Work Order?${params}`, window.location.origin)
	const response = await fetch(url)
	const { data }: { data: WorkOrder[] } = await response.json()

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
