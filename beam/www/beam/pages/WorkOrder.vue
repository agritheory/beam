<template>
	<!-- navigation section -->
	<Navbar>
		<template #title>
			<h1 class="nav-title">Manufacture</h1>
			<span v-if="store.form.dirty" class="nav-subtitle" )>Unsaved changes</span>
		</template>
		<template #navbaraction>
			<RouterLink :to="{ name: 'home' }">Home</RouterLink>
		</template>
	</Navbar>

	<!-- body section -->
	<BeamMetadata class="box">
		<div style="padding: 1rem">
			<SplitColumn>
				<template #left>
					<p class="beam_metadata_heading">{{ workOrder.production_item }}</p>
					<p class="beam--norma">{{ totalTransferred }} / {{ totalToTransfer }} ({{ transferredPercent }}%)</p>
				</template>
				<template #right>
					<p class="beam--normal">{{ workOrder.planned_start_date }}</p>
					<p class="beam--norma">{{ operationsCompleted }} / {{}} ({{ completedOperationsPercentage }}%)</p>
				</template>
			</SplitColumn>
		</div>
	</BeamMetadata>
	<div class="box" v-show="items.length">
		<ListView :items="items" :key="refreshKey" />
	</div>
	<div class="box" v-show="operations.length">
		<ListView :items="operations" :key="refreshKey" />
	</div>

	<!-- footer section -->
	<ControlButtons :buttons="controlButtons" />
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import ControlButtons from '@/components/ControlButtons.vue'
import { useBeamStore } from '@/stores/beam'
import type { ListViewItem, StockEntry, WorkOrder } from '@/types'

// TODO:
// 1. subscribe on changes to required items
// 2. listen on changes from emit in ListCount

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

onMounted(async () => {
	if (!store.cache.mappers[workOrderId]) {
		// create and save a Stock Entry mapped to the Work Order into cache
		stockEntry.value = await store.getMappedStockEntry({
			work_order_id: workOrderId,
			purpose: 'Material Transfer for Manufacture',
		})

		store.$patch(state => {
			state.cache.mappers[workOrderId] = stockEntry.value
		})
	}
})

const items = computed((): ListViewItem[] => {
	return (
		stockEntry.value?.items.map(item => ({
			...item,
			label: item.item_code,
			count: { count: item.qty, of: item.transfer_qty },
			linkComponent: 'ListCount',
		})) || []
	)
})

const operations = computed((): ListViewItem[] => {
	return workOrder.value.operations.map(operation => ({
		...operation,
		label: operation.operation,
		count: { count: operation.completed_qty, of: workOrder.value.qty },
		linkComponent: 'ListAnchor',
		description: `${operation.workstation} - ${operation.time_in_mins}:00`,
		route: `#/work_order/${workOrder.value.name}/operation/${operation.name}`,
	}))
})

const create = async () => {
	if (store.form.dirty) {
		const document: StockEntry = { ...stockEntry.value }
		document.items = document.items.filter(item => item.qty > 0)
		const response = await store.insert('Stock Entry', document)

		if (!response.exception) {
			store.$patch(state => {
				state.form.dirty = false
				state.cache.mappers[workOrderId] = response.data
				stockEntry.value = response.data
			})
		}

		return response
	} else {
		// TODO: a few options here:
		// 1. allow setting a condition in ControlButtons to control when to enable the button
		// 2. add a toast message here telling the user why this is a no-op
	}
}

const submit = async () => {
	throw new Error('Not implemented')
}

const cancel = async () => {
	throw new Error('Not implemented')
}

const controlButtons = computed(() => {
	if (!workOrder) {
		return []
	}
	return [
		{
			label: 'SAVE',
			action: create,
			disabled: items.value.length === 0,
			color: { background: '#4791FF', text: 'var(--sc-btn-color)' },
		},
		{
			label: workOrder.value.skip_transfer ? 'MANUFACTURE' : 'TRANSFER',
			action: () => store.submit<StockEntry>('Stock Entry', stockEntry),
			disabled: stockEntry.value.items.length === 0 || !stockEntry.value.name,
			color: { background: 'var(--sc-success)', text: 'var(--sc-btn-color)' },
		},
		{
			label: 'CANCEL',
			action: () => store.cancel<StockEntry>('Stock Entry', stockEntry),
			disabled: stockEntry.value.items.length === 0 || !stockEntry.value.name,
			hidden: stockEntry.value.docstatus != 1,
			color: { background: 'var(--sc-alert)', text: 'var(--sc-btn-color)' },
		},
	]
})

const totalTransferred = computed((): number => {
	return items.value.reduce((sum, item) => sum + item.qty, 0)
})

const totalToTransfer = computed((): number => {
	return items.value.reduce((sum, item) => sum + item.transfer_qty, 0)
})

const transferredPercent = computed((): string => {
	const total = totalToTransfer.value
	if (total === 0) return '0'
	return `${((totalTransferred.value / total) * 100).toFixed(0)}`
})

const operationsCompleted = computed((): number => {
	return operations.value.reduce((sum, operation) => sum + operation.completed_qty, 0) || 0
})

const totalOperations = computed((): number => {
	return workOrder.value.qty * operations.value.length
})

const completedOperationsPercentage = computed((): string => {
	const target = operationsCompleted.value
	if (target === 0) return '0'
	return `${((totalOperations.value / target) * 100).toFixed(0)}`
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
