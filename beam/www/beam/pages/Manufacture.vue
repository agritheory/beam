<template>
	<h3>Work Orders</h3>
	<ListView :items="orders" />
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import type { WorkOrder } from '../types'

const orders = ref([])

onMounted(async () => {
	const params = new URLSearchParams({
		fields: JSON.stringify(['name', 'item_name AS label', 'qty', 'produced_qty']),
		order_by: 'creation asc',
	})

	const url = new URL(`/api/resource/Work Order?${params}`, window.location.origin)
	const response = await fetch(url)
	const { data }: { data: Partial<WorkOrder>[] } = await response.json()
	data.forEach(row => {
		orders.value.push({
			...row,
			count: { count: row.produced_qty, of: row.qty },
			linkComponent: 'ListAnchor',
			route: `#/work_order/${row.name}`,
		})
	})
	orders.value = data
})
</script>
