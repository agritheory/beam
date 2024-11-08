<template>
	<Navbar>
		<template #title>
			<h1 class="nav-title">Manufacture</h1>
			<span v-if="store.form.dirty" class="nav-subtitle">Unsaved changes</span>
		</template>
		<template #navbaraction>
			<RouterLink :to="{ name: 'home' }">Home</RouterLink>
		</template>
	</Navbar>

	<div>
		<p>Planned Start: {{ (store.form as WorkOrder).planned_start_date }}</p>
	</div>
	<div class="box" v-show="items.length">
		<ListView :items="items" />
	</div>
	<div class="box" v-show="operations.length">
		<ListView :items="operations" />
	</div>
	<ControlButtons
		:onCreate="create"
		:onSubmit="() => store.submit<WorkOrder>('Work Order', workOrderId)"
		:onCancel="() => store.cancel<WorkOrder>('Work Order', workOrderId)" />
</template>

<script setup lang="ts">
import { computed, onMounted, ref, reactive, watch } from 'vue'
import { useRoute } from 'vue-router'

import ControlButtons from '@/components/ControlButtons.vue'
import { useDataStore } from '@/store'
import type { StockEntry, ListViewItem, WorkOrder } from '@/types'

const route = useRoute()
const store = useDataStore()
const workOrderId = route.params.id.toString()
const stockEntry = ref<Partial<StockEntry>>({})
let order = reactive({})
const operations = ref<ListViewItem[]>([])
const items = ref<ListViewItem[]>([])

onMounted(async () => {
	order = store.form as Partial<WorkOrder>

	operations.value = order.operations.map(operation => ({
		...operation,
		label: operation.operation,
		count: { count: operation.completed_qty, of: order.qty },
		linkComponent: 'ListAnchor',
		route: `#/work_order/${order.name}/operation/${operation.name}`,
	}))
	items.value = order.required_items.map(item => ({
		...item,
		transfer_qty: 0, // use this field as the one to transfer against
		label: item.item_code,
		count: { count: item.transferred_qty, of: item.required_qty },
		linkComponent: 'ListCount',
	}))
})
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
