<template>
	<Navbar @click="handlePrimaryAction">
		<template #title>
			<h1 class="nav-title">{{ store.form.name }}</h1>
		</template>
		<template #navbaraction>Home</template>
	</Navbar>

	<!-- <div>
		<p>Planned Start: {{ store.form.planned_start_date }}</p>
	</div> -->
	<BeamMetadata :order="workOrder" />

	<br />

	<div class="box">
		<Transfer :id="workOrderId" />
	</div>

	<div class="box" v-show="operations.length">
		<ListView :items="operations" />
	</div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import Transfer from '@/components/Transfer.vue'
import { useDataStore } from '@/store'
import type { /* JobCard, */ ListViewItem, WorkOrder } from '@/types'

const route = useRoute()
const store = useDataStore()
const workOrderId = route.params.orderId.toString()

const workOrder = ref({
	orderNumber: workOrderId,
	product: '',
	quantity: 0,
	total: 0,
	complete: false,
})

// const jobCards = ref<ListViewItem[]>([])
const operations = ref<ListViewItem[]>([])

onMounted(async () => {
	const order = store.form as Partial<WorkOrder>

	// build operation list
	operations.value = order.operations.map(operation => ({
		...operation,
		label: operation.operation,
		count: { count: operation.completed_qty, of: order.qty },
		linkComponent: 'ListAnchor',
		route: `#/work_order/${workOrderId}/operation/${operation.name}`,
	}))

	workOrder.value = {
		...workOrder.value,
		product: order.item_name,
		quantity: order.produced_qty,
		total: order.qty,
		complete: order.status === "Complete",
	}
	// get job cards
	// for (const operation of order.operations) {
	// 	const jobList = await store.getAll<JobCard[]>('Job Card', {
	// 		filters: JSON.stringify([['operation_id', '=', operation.name]]),
	// 	})

	// 	for (const job of jobList) {
	// 		const jobCard = await store.getOne<JobCard>('Job Card', job.name)
	// 		jobCards.value.push({
	// 			...jobCard,
	// 			label: jobCard.name,
	// 			count: { count: jobCard.total_time_in_mins, of: operation.time_in_mins },
	// 			linkComponent: 'ListAnchor',
	// 			route: `#/job_card/${workOrderId}`,
	// 		})
	// 	}
	// }
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
