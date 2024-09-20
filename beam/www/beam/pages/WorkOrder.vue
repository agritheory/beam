<template>
	<Navbar @click="handlePrimaryAction">
		<template #title>
			<h1 class="nav-title">{{ workOrder.name }}</h1>
		</template>
		<template #navbaraction>Home</template>
	</Navbar>
	<div>
		<p>Planned Start: {{ workOrder.planned_start_date }}</p>
	</div>
	<br />
	<div class="box">
		<Transfer :items="workOrder?.required_items" :id="workOrderId" />
	</div>
	<div class="box">
		<ListView :items="operations" />
	</div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import Transfer from '../components/Transfer.vue'
import { useDataStore } from '../store'
import type { JobCard, ListViewItem, WorkOrder } from '../types'

const route = useRoute()
const store = useDataStore()
const workOrderId = route.params.orderId.toString()

const workOrder = ref<Partial<WorkOrder>>({})
const operations = ref<ListViewItem[]>([])
const jobCards = ref<ListViewItem[]>([])
const items = ref<ListViewItem[]>([])

onMounted(async () => {
	// get work order
	workOrder.value = await store.getOne<WorkOrder>('Work Order', workOrderId)
	workOrder.value.required_items = workOrder.value.required_items.map(item => ({
		...item,
		wip_warehouse: workOrder.value.wip_warehouse,
	}))

	// build operation list
	operations.value = workOrder.value.operations.map(operation => ({
		...operation,
		label: operation.operation,
		count: { count: operation.completed_qty, of: workOrder.value.qty },
		linkComponent: 'ListAnchor',
		route: `#/work_order/${workOrderId}/operation/${operation.name}`,
	}))

	items.value = workOrder.value.required_items.map(item => ({
		...item,
		label: item.item_code,
		count: { count: item.transferred_qty, of: item.required_qty },
		linkComponent: 'ListItem',
		description: `${item.source_warehouse}`,
	}))

	// get job cards
	for (const operation of workOrder.value.operations) {
		const jobList = await store.getAll<JobCard[]>('Job Card', {
			filters: JSON.stringify([['operation_id', '=', operation.name]]),
		})

		if (jobList.length === 0) {
			continue
		}

		for (const job of jobList) {
			const jobCard = await store.getOne<JobCard>('Job Card', job.name)
			jobCards.value.push({
				...jobCard,
				label: jobCard.name,
				count: { count: jobCard.total_time_in_mins, of: operation.time_in_mins },
				linkComponent: 'ListAnchor',
				route: `#/job_card/${workOrderId}`,
			})
		}
	}
})

const handlePrimaryAction = () => {
	console.log('handle primary action')
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
</style>
