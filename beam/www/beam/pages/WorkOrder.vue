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
		<p>Planned Start: {{ workOrder.planned_start_date }}</p>
	</div>
	<div class="box" v-show="items.length">
		<ListView :items="items" :key="refreshKey" />
	</div>
	<div class="box" v-show="operations.length">
		<ListView :items="operations" :key="refreshKey" />
	</div>

	<!-- footer section -->
	<ControlButtons :onCreate="create" :onSubmit="submit" :onCancel="cancel" />
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
