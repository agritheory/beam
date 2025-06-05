<template>
	<!-- navigation section -->
	<Navbar>
		<template #title>
			<h1>{{ workOrderId || 'Work Order' }}</h1>
			<span v-if="stockEntry?.dirty" class="dirty">Unsaved</span>
		</template>
		<template #navbaraction>
			<RouterLink :to="{ name: 'home' }">Home</RouterLink>
		</template>
	</Navbar>

	<!-- scan section -->
	<ScanOutput />

	<!-- body section -->
	<BeamMetadata class="box">
		<div style="padding: 1rem">
			<SplitColumn>
				<template #left>
					<p class="beam_metadata_heading">{{ workOrder.production_item }}</p>
					<p class="beam--normal">
						{{ transferProgress.transferred }} / {{ transferProgress.total }} ({{ transferProgress.percent }}%)
					</p>
				</template>
				<template #right>
					<p class="beam--normal">{{ workOrder.planned_start_date }}</p>
					<p class="beam--normal">
						{{ operationProgress.completed }} / {{ operationProgress.total }} ({{ operationProgress.percent }}%)
					</p>
				</template>
			</SplitColumn>
		</div>
	</BeamMetadata>
	<div class="box" v-show="items.length">
		<ListView :items="items" @update="updateItem" :key="refreshKey" />
	</div>
	<div class="box" v-show="operations.length">
		<ListView :items="operations" :key="refreshKey" />
	</div>

	<!-- footer section -->
	<ControlButtons :buttons="controlButtons" />
</template>

<script setup lang="ts">
import type { ListViewItem } from '@stonecrop/beam'
import { computed, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'

import ControlButtons from '@/components/ControlButtons.vue'
import ScanOutput from '@/components/ScanOutput.vue'
import { useBeamStore } from '@/stores/beam'
import type {
	ControlButton,
	DocActionResponse,
	StockEntry,
	StockEntryItem,
	WorkOrder,
	WorkOrderItem,
	WorkOrderOperation,
} from '@/types'

// TODO: subscribe on changes to required items

type OrderItem = WorkOrderItem & StockEntryItem & ListViewItem
type OrderOperation = WorkOrderOperation & ListViewItem

const route = useRoute()
const store = useBeamStore()
const workOrderId = route.params.id.toString()

const stockEntry = ref<StockEntry | undefined>(store.cache.mappers[workOrderId] as StockEntry)
const workOrder = ref(store.form as WorkOrder)
const refreshKey = ref(0)

// hack: since array reactivity is not present in Vue 3, force-refresh the listviews on store update
store.$subscribe(mutation => {
	if (['patch function', 'patch object'].includes(mutation.type)) {
		refreshKey.value++
	}
})

const items = computed((): OrderItem[] => {
	if (!stockEntry.value) return []
	return workOrder.value.required_items.map(item => {
		const stockEntryItem = stockEntry.value.items.find(i => i.item_code === item.item_code)
		return {
			...stockEntryItem,
			...item,
			label: item.item_code,
			count: { count: stockEntryItem?.qty || item.transferred_qty, of: item.required_qty },
			linkComponent: 'ListCount',
		}
	})
})

const operations = computed((): OrderOperation[] => {
	return workOrder.value.operations.map(operation => ({
		...operation,
		label: operation.operation,
		count: { count: operation.completed_qty, of: workOrder.value.qty },
		linkComponent: 'ListAnchor',
		description: `${operation.workstation} - ${operation.time_in_mins}:00`,
		route: `#/work_order/${workOrder.value.name}/operation/${operation.name}`,
	}))
})

const transferProgress = reactive({
	transferred: computed(() => items.value.reduce<number>((sum, item) => sum + (item.qty || item.transferred_qty), 0)),
	total: computed(() => items.value.reduce<number>((sum, item) => sum + item.required_qty, 0)),
	percent: computed(() =>
		transferProgress.total === 0 ? '0' : `${((transferProgress.transferred / transferProgress.total) * 100).toFixed(0)}`
	),
})

const operationProgress = reactive({
	completed: computed(() => operations.value.reduce((sum, operation) => sum + operation.completed_qty, 0) || 0),
	total: computed(() => workOrder.value.qty * operations.value.length),
	percent: computed(() =>
		operationProgress.total === 0
			? '0'
			: `${((operationProgress.completed / operationProgress.total) * 100).toFixed(0)}`
	),
})

const controlButtons = computed((): ControlButton[] => {
	if (!workOrder) return []

	const form = stockEntry.value as StockEntry
	if (!form || !form.items) return []

	return [
		{
			label: stockEntry.value.name ? 'UPDATE' : 'SAVE',
			disabled: items.value.length === 0,
			color: { background: '#4791FF', text: 'var(--sc-btn-color)' },
			action: upsertStockEntry,
		},
		{
			label: workOrder.value.skip_transfer ? 'MANUFACTURE' : 'TRANSFER',
			disabled: form.items.length === 0 || !form.name,
			hidden: Boolean(form.__islocal) || form.docstatus !== 0,
			color: { background: 'var(--sc-success)', text: 'var(--sc-btn-color)' },
			action: async () => await store.submit<StockEntry>('Stock Entry', form.name),
		},
		{
			label: 'CANCEL',
			disabled: form.items.length === 0 || !form.name,
			hidden: Boolean(form.__islocal) || form.docstatus !== 1,
			color: { background: 'var(--sc-alert)', text: 'var(--sc-btn-color)' },
			action: async () => await store.cancel<StockEntry>('Stock Entry', form.name),
		},
	]
})

const updateItem = (value: OrderItem) => {
	let itemModified = false
	for (const item of stockEntry.value.items) {
		if (item.item_code === value.item_code && item.qty !== value.count.count) {
			item.qty = value.count.count
			itemModified = true
			break
		}
	}

	if (itemModified) {
		store.$patch(state => {
			stockEntry.value.dirty = true
			state.cache.mappers[workOrderId] = stockEntry.value
		})
	}
}

const upsertStockEntry = async () => {
	if (stockEntry.value.dirty) {
		const document: StockEntry = { ...stockEntry.value }
		document.items = document.items.filter(item => item.qty > 0)

		let response: DocActionResponse<StockEntry>
		if (stockEntry.value.name) {
			response = await store.update('Stock Entry', document.name, document)
		} else {
			response = await store.insert('Stock Entry', document)
		}

		if (!response.exception) {
			store.$patch(state => {
				stockEntry.value = response.data
				stockEntry.value.dirty = false
				state.cache.mappers[workOrderId] = stockEntry.value
			})
		}
	} else {
		// TODO: a few options here:
		// 1. allow setting a condition in ControlButtons to control when to enable the button
		// 2. add a toast message here telling the user why this is a no-op
	}
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
	padding: 0rem;
	margin: 0.5rem;
	font-size: 100%;
	border: 2px solid gray;
	outline: 2px solid transparent;
	flex: 1;
	min-width: 100px;
}

.dirty {
	color: tomato;
	font-weight: 700;
}
</style>
