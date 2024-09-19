<template>
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

import { useDataStore } from '../store'
import type { JobCard, WorkOrder, WorkOrderOperation } from '../types'

const route = useRoute()
const store = useDataStore()

const workOrder = ref<Partial<WorkOrder>>({})
const operation = ref<Partial<WorkOrderOperation>>({})
const jobCard = ref<Partial<JobCard>>({})

const operationStarted = computed(() =>
	isNaN(jobCard.value.total_time_in_mins) ? false : jobCard.value.total_time_in_mins > 0
)

const elapsedTime = computed(() => {
	const date = new Date(0)
	date.setSeconds(jobCard.value.total_time_in_mins * 60)
	return isNaN(date.getTime()) ? '00:00:00' : date.toISOString().substring(11, 19)
})

onMounted(async () => {
	workOrder.value = await store.getOne<WorkOrder>('Work Order', route.params.orderId.toString())
	operation.value = workOrder.value.operations.find(operation => operation.name === route.params.id) || {}

	const jobList = await store.getAll<JobCard[]>('Job Card', {
		filters: JSON.stringify([['operation_id', '=', route.params.id]]),
	})

	if (jobList.length > 0) {
		jobCard.value = await store.getOne<JobCard>('Job Card', jobList[0].name)
	}
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
