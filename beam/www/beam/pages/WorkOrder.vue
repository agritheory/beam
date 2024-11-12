<template>
	<!-- navigation section -->
	<Navbar>
		<template #title>
			<h1 class="nav-title">Manufacture</h1>
			<span v-if="store.form.dirty" class="nav-subtitle">Unsaved changes</span>
		</template>
		<template #navbaraction>
			<RouterLink :to="{ name: 'home' }">Home</RouterLink>
		</template>
	</Navbar>

	<!-- body section -->
	<div>
		<p>Planned Start: {{ order.planned_start_date }}</p>
	</div>
	<div class="box" v-show="items.length">
		<ListView :items="items" :key="refreshKey" />
	</div>
	<div class="box" v-show="operations.length">
		<ListView :items="operations" :key="refreshKey" />
	</div>

	<!-- footer section -->
	<ControlButtons
		:onCreate="create"
		:onSubmit="() => store.submit<WorkOrder>('Work Order', workOrderId)"
		:onCancel="() => store.cancel<WorkOrder>('Work Order', workOrderId)" />
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'

import ControlButtons from '@/components/ControlButtons.vue'
import { useBeamStore } from '@/stores/beam'
import type { ListViewItem, WorkOrder } from '@/types'

const route = useRoute()
const store = useBeamStore()
const workOrderId = route.params.id.toString()

const order = ref(store.form as WorkOrder)
const refreshKey = ref(0)

store.$subscribe((mutation, state) => {
	if (['patch function', 'patch object'].includes(mutation.type)) {
		order.value = state.form as WorkOrder
		refreshKey.value++
	}
})

const items = computed((): ListViewItem[] => {
	return order.value.required_items.map(item => ({
		...item,
		transfer_qty: 0, // use this field as the one to transfer against
		label: item.item_code,
		count: { count: item.transferred_qty, of: item.required_qty },
		linkComponent: 'ListCount',
	}))
})

const operations = computed((): ListViewItem[] => {
	return order.value.operations.map(operation => ({
		...operation,
		label: operation.operation,
		count: { count: operation.completed_qty, of: order.value.qty },
		linkComponent: 'ListAnchor',
		route: `#/work_order/${order.value.name}/operation/${operation.name}`,
	}))
})

// TODO:
// 1. subscribe on changes to required items
// 2. listen on changes from emit in ListCount

const create = async () => {
	throw new Error('Not implemented')
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
