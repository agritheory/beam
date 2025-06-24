<template>
	<Navbar>
		<template #title>
			<h1>Reconciliation</h1>
		</template>
		<template #navbaraction>
			<RouterLink :to="{ name: 'home' }">Home</RouterLink>
		</template>
	</Navbar>

	<div class="reconciliation">
		<div class="dropdown-container">
			<ADropdown label="Warehouse" :items="warehouseList" v-model="reconciliation.set_warehouse" />
			<BeamBtn class="clear-button" @click="clearField()"> X </BeamBtn>
		</div>
	</div>

	<!-- body section -->
	<ListView v-if="items.length > 0" :items="items" :key="componentKey" @update="updateItem" />
	<div class="begin" v-else>
		<span>Scan or Select Warehouses to Begin</span>
	</div>
	<!-- footer section -->
	<ControlButtons :buttons="controlButtons" />
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import ControlButtons from '@/components/ControlButtons.vue'
import { useBeamStore } from '@/stores/beam'
import type { ControlButton, StockReconciliation, StockEntryItem } from '@/types'
import ListView from '@/components/ListView.vue'

const store = useBeamStore()
const componentKey = ref(0)
const reconciliation = computed(
	(): StockReconciliation =>
		(store.cache.mappers['stock-reconciliation'] as StockReconciliation) || {
			name: '',
			purpose: 'Stock Reconciliation',
			items: [],
			set_warehouse: '',
		}
)
const items = computed((): StockEntryItem[] => reconciliation.value.items)
const warehouseList = ref<string[]>([])

store.$subscribe(mutation => {
	if (['patch function', 'patch object'].includes(mutation.type)) {
		componentKey.value++
	}
})

onMounted(async () => {
	store.$patch(state => ((state.cache.mappers['stock-reconciliation'] as StockReconciliation) = reconciliation.value))
	warehouseList.value = store.warehouseList.filter(w => !w.is_group).map(w => w.name)
})

const clearField = () => store.$patch(state => (state.cache.mappers['stock-reconciliation']['set_warehouse'] = ''))

const loadItems = async warehouse => {
	try {
		let response = await store.getStockReconciliationItems(warehouse)
		if (!response || response.length === 0) return
		response = response.map(item => ({
			...item,
			debounce: 1000,
			label: item.item_code,
			count: { count: item.qty, uom: item.stock_uom },
			linkComponent: 'ListCount',
		}))
		store.$patch(state => ((state.cache.mappers['stock-reconciliation'] as StockReconciliation).items = response))
	} catch (error) {
		console.error('Error loading items:', error)
	}
}

type StockEntryItemWithCount = StockEntryItem & { count?: { count: number; of?: number } }
const create = async () => {
	const body = {
		purpose: 'Stock Reconciliation',
		set_warehouse: reconciliation.value.set_warehouse,
		items: (items.value as StockEntryItemWithCount[]).map(i => ({
			...i,
			qty: typeof i.count === 'object' ? i.count.count : i.qty,
		})),
		name: reconciliation.value.name,
	}
	console.log(body)
	let res
	if (body.name) {
		res = await store.update('Stock Reconciliation', body.name, body)
	} else {
		res = await store.insert('Stock Reconciliation', body)
	}
	const { data } = res
	console.log(data)
	if (data && data.name) {
		reconciliation.value.name = data.name
	}
	return res
}

const submit = async () => {
	if (!reconciliation.value.name) return
	const res = await store.submit('Stock Reconciliation', reconciliation.value.name)
	if (res?.data) {
		store.$patch(state => {
			;(state.cache.mappers['stock-reconciliation'] as any) = {
				name: '',
				purpose: 'Stock Reconciliation',
				items: [],
				set_warehouse: '',
			}
		})
	}
}

const cancel = async () => {
	store.$patch(state => {
		;(state.cache.mappers['stock-reconciliation'] as any) = {
			name: '',
			purpose: 'Stock Reconciliation',
			items: [],
			set_warehouse: '',
		}
	})
}

const controlButtons = computed((): ControlButton[] => {
	if (!items.value.length || !reconciliation.value.set_warehouse) return []
	return [
		{
			label: 'SAVE',
			disabled: items.value.length === 0,
			color: { background: '#4791FF', text: 'var(--sc-btn-color)' },
			action: create,
		},
		{
			label: 'SUBMIT',
			disabled: !reconciliation.value.name,
			hidden: !reconciliation.value.name,
			color: { background: 'var(--sc-success)', text: 'var(--sc-btn-color)' },
			action: submit,
		},
		{
			label: 'CANCEL',
			color: { background: 'white', text: 'black' },
			action: cancel,
		},
	]
})

watch(
	() => reconciliation.value.set_warehouse,
	warehouse => {
		if (!warehouse) return
		loadItems(warehouse)
	}
)

const updateItem = (value: StockEntryItemWithCount) => {
	if (!value || !value.count || !value.count.count) return
	let itemModified = false
	for (const item of reconciliation.value.items) {
		if (item.item_code === value.item_code && item.qty !== value.count.count) {
			item.qty = value.count.count
			itemModified = true
			break
		}
	}

	if (itemModified) {
		store.$patch(state => ((state.cache.mappers['stock-reconciliation'] as StockEntryItem) = reconciliation.value))
	}
}
</script>
<style>
.reconciliation {
	margin-bottom: 1.5em;
}

.reconciliation .autocomplete input,
.autocomplete-results {
	font-size: 150%;
}

.autocomplete-results {
	padding-inline: 3px !important;
}

.reconciliation .input-wrapper label {
	margin: calc(-2.5rem - calc(2.15rem / 2)) 0 0 1ch !important;
}
</style>
