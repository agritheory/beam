<template>
	<h1>Job Cards</h1>

	<li v-for="operation in workOrder.operations">
		<router-link :to="{ name: 'operation', params: { workOrder: route.params.id, id: operation.name } }">
			<span>{{ operation.operation }}</span>
			<span class="right-align"> ({{ operation.completed_qty }} / {{ workOrder.qty }})</span>
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
	const response = await fetch(`/api/resource/Work Order/${route.params.id}`)
	const { data }: { data: Partial<WorkOrder> } = await response.json()
	workOrder.value = data
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
