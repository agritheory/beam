<template>
	<h1>Job Cards</h1>

	<li v-for="operation in workOrder.operations">
		<router-link :to="{ name: 'operation', params: { workOrder: route.params.id, id: operation.name } }">
			<span>{{ operation.operation }}</span>
			<span class="right-align"> ({{ workOrder.qty }} / {{ operation.completed_qty }})</span>
		</router-link>
	</li>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import type { WorkOrder } from '../types'

const route = useRoute()
const workOrder = ref<Partial<WorkOrder>>({})

onMounted(async () => {
	// avoid CSRF-token errors on reloading a page
	frappe.csrf_token = window.csrf_token

	const response = await frappe.call({
		method: 'frappe.client.get',
		args: {
			doctype: 'Work Order',
			name: route.params.id,
		},
	})
	workOrder.value = response.message as WorkOrder
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
	border-bottom: 2px solid grey;
	display: flex;
	justify-content: space-between;
	padding: 10px;
}

li:active {
	border-bottom: 2px solid ble;
}

.right-align {
	margin-left: auto;
}
</style>
