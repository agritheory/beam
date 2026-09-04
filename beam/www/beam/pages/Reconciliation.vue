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
	<ListView v-if="items.length > 0" :items="items" :key="componentKey" />
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
type StockEntryItemWithCount = StockEntryItem & {
	warehouse?: string
	count?: { count: number; of: number; uom?: string }
}

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
const items = ref([] as StockEntryItem[])
const warehouseList = ref<string[]>([])

const clearField = () => {
	store.$patch(state => (state.cache.mappers['stock-reconciliation']['set_warehouse'] = ''))
	store.$patch(state => ((state.cache.mappers['stock-reconciliation'] as StockReconciliation).items = []))
	items.value = []
}

const resetItems = () => {
	store.$patch(state => ((state.cache.mappers['stock-reconciliation'] as StockReconciliation).items = []))
	items.value = []
}

const mergeItems = (newItems: StockEntryItem[], fromWarehouse?: Boolean) => {
	if (!newItems) return

	newItems.forEach(newItem => {
		const existingItem = items.value.find(item => item.item_code === newItem.item_code) as
			| StockEntryItemWithCount
			| undefined

		if (existingItem) {
			Object.assign(existingItem, newItem)
			existingItem.label = newItem.item_code
			existingItem.debounce = 1000
			if (!fromWarehouse && existingItem.count) {
				existingItem.count.count += 1
			}
		} else {
			items.value.push({
				...newItem,
				label: newItem.item_code,
				count: {
					count: newItem.qty || 1,
					of: 0,
					uom: newItem.stock_uom,
				},
				debounce: 1000,
			} as StockEntryItemWithCount)
		}
	})
}

let activeWarehouse = ''

const loadItemsFromWarehouse = async warehouse => {
	if (!warehouse) return
	activeWarehouse = warehouse
	try {
		let response = await store.getStockReconciliationItems(warehouse)
		if (warehouse !== activeWarehouse) return
		mergeItems(response || [], true)
	} catch (error) {
		console.error('Error loading items:', error)
	}
}

const create = async () => {
	const warehouse = reconciliation.value.set_warehouse
	const body = {
		purpose: 'Stock Reconciliation',
		set_warehouse: warehouse,
		items: (items.value as StockEntryItemWithCount[]).map(i => {
			const { count, label, debounce, ...rest } = i
			return {
				...rest,
				warehouse: rest.warehouse || warehouse,
				qty: typeof count === 'object' ? count.count : rest.qty,
			}
		}),
		name: reconciliation.value.name,
	}

	let res
	if (body.name) {
		res = await store.update('Stock Reconciliation', body.name, body)
	} else {
		res = await store.insert('Stock Reconciliation', body)
	}
	const { data } = res
	if (data && data.name) reconciliation.value.name = data.name
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
		items.value = []
		componentKey.value++
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
	items.value = []
	componentKey.value++
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
		resetItems()
		loadItemsFromWarehouse(warehouse)
	}
)

watch(
	() => store.cache.mappers['stock-reconciliation']?.items,
	newItems => mergeItems(newItems || []),
	{ immediate: true, deep: true }
)

onMounted(async () => {
	store.$patch(state => ((state.cache.mappers['stock-reconciliation'] as StockReconciliation) = reconciliation.value))
	warehouseList.value = store.warehouseList.filter(w => !w.is_group).map(w => w.name)
})
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

.beam_item-count {
	white-space: nowrap;
}
</style>
