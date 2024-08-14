<template>
	<h3>Work Order</h3>
	<div class="container">
		<div class="box">
			{{ operation.description }}
		</div>
		<div class="box fix-height">
			<b class>{{ elapsedTime }}</b>
			<button :disabled="!operationStarted" @click="startOperation">Start</button>
			<button :disabled="operationStarted" @click="stopOperation">Stop</button>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import type { JobCard, WorkOrder, WorkOrderOperation } from '../types'

const route = useRoute()
const workOrder = ref<Partial<WorkOrder>>({})
const operation = ref<Partial<WorkOrderOperation>>({})
const jobCard = ref<Partial<JobCard>>({})

const operationStarted = computed(() =>
	isNaN(jobCard.value.total_time_in_mins) ? false : jobCard.value.total_time_in_mins > 0
)
const elapsedTime = computed(() => {
	const date = new Date(0)
	date.setSeconds(jobCard.value.total_time_in_mins * 60)
	if (isNaN(date.getTime())) {
		return '00:00:00'
	}
	return date.toISOString().substring(11, 19)
})

onMounted(async () => {
	// avoid CSRF-token errors on reloading a page
	frappe.csrf_token = window.csrf_token

	const order = await frappe.call({
		method: 'frappe.client.get',
		args: {
			doctype: 'Work Order',
			name: route.params.workOrder,
		},
	})

	workOrder.value = order.message as WorkOrder
	operation.value = workOrder.value.operations.find(operation => operation.name === route.params.id) || {}

	const jobCardCheck = await frappe.call({
		method: 'frappe.client.get_count',
		args: {
			doctype: 'Job Card',
			filters: {
				operation_id: route.params.id,
			},
		},
	})

	if (jobCardCheck.message === 0) {
		return
	}

	const jobCard = await frappe.call({
		method: 'frappe.client.get',
		args: {
			doctype: 'Job Card',
			filters: {
				operation_id: route.params.id,
			},
		},
	})
	jobCard.value = jobCard.message as JobCard
})

const startOperation = () => {
	// TODO: action here
	alert('Timer Started')
}

const stopOperation = () => {
	// TODO: action here
	alert('Timer Stopped')
}
</script>

<style scoped>
b {
	display: flex;
	justify-content: center;
	align-items: center;
}
.container {
	display: flex;
	gap: 20px;
	/* Space between the boxes */
}

.box {
	padding: 2rem;
	margin: 0.5rem;
	font-size: 100%;
	border: 2px solid gray;
	outline: 2px solid transparent;
	flex: 1;
	min-width: 100px;
}

.fix-height {
	height: 7rem;
	font-size: 150%;
	text-align: center;
	display: grid;
	grid-template-columns: repeat(3, 1fr);
	gap: 20px;
}
</style>
