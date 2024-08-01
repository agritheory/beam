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

const workOrders = ref<WorkOrder[]>([])

onMounted(async () => {
	// avoid CSRF-token errors on reloading a page
	frappe.csrf_token = window.csrf_token

	const response = await frappe.call({
		method: 'frappe.client.get_list',
		args: {
			doctype: 'Work Order',
			order_by: 'creation',
			fields: ['name', 'item_name'],
		},
	})
	workOrders.value = response.message as WorkOrder[]
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
