<template>
	<h1>Work Order</h1>

	<li v-for="workOrder in workOrders">
		<router-link :to="{ name: 'job_card', params: { id: workOrder.name } }">
			{{ workOrder.item_name }} ({{ workOrder.name }})
		</router-link>
	</li>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import type { WorkOrder } from '../types'

const workOrders = ref<Partial<WorkOrder>[]>([])

onMounted(async () => {
	const params = new URLSearchParams({
		fields: JSON.stringify(['name', 'item_name']),
		order_by: 'creation asc',
	})

	const url = new URL(`/api/resource/Work Order?${params}`, window.location.origin)
	const response = await fetch(url)
	const { data }: { data: Partial<WorkOrder>[] } = await response.json()
	workOrders.value = data
})
</script>

<style scoped>
div {
	padding-top: 0.5rem;
}

li {
	list-style: none;
	padding: 2rem;
	margin: 0.5rem;
	font-size: 150%;
	border: 2px solid gray;
	outline: 2px solid transparent;
}

li:active {
	outline: 2px solid gray;
}
</style>
