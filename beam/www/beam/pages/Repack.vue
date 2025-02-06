<template>
	<Navbar>
		<template #title>
			<h1>Repack</h1>
		</template>
		<template #navbaraction>
			<RouterLink :to="{ name: 'home' }">Home</RouterLink>
		</template>
	</Navbar>

	<div class="move">
		<!-- <ADropdown label="Item to Repack" :items="itemList" v-model="stockEntry.item" />
		<AInput label="Qty" type="number" v-model="stockEntry.qty" />
		<ADropdown label="BOM (Optional)" :items="bomList" v-model="stockEntry.bom" /> -->

		<div class="dropdown-container">
			<ADropdown label="Source Warehouse" :items="warehouseList" v-model="stockEntry.from_warehouse" />
			<BeamBtn class="clear-button" @click="clearField('from_warehouse')"> X </BeamBtn>
		</div>
		<div class="dropdown-container">
			<ADropdown label="Target Warehouse" :items="warehouseList" v-model="stockEntry.to_warehouse" />
			<BeamBtn class="clear-button" @click="clearField('to_warehouse')"> X </BeamBtn>
		</div>
	</div>

	<ListView :items="items" :key="componentKey" @update="update" />
	<div class="begin" v-if="items.length == 0">
		<span>Scan Items, Select Warehouses, and Set Qty to Begin</span>
	</div>

	<ControlButtons :buttons="controlButtons" />
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useBeamStore } from '@/stores/beam'
import ControlButtons from '@/components/ControlButtons.vue'
import type { ListViewItem } from '@stonecrop/beam'
import type { ControlButton, StockEntry } from '@/types'

const store = useBeamStore()
const items = ref<ListViewItem[]>([])
const componentKey = ref(0)
const stockEntry = computed(
	(): StockEntry =>
		(store.cache.mappers['repack'] as StockEntry) || {
			name: '',
			stock_entry_type: 'Repack',
			items: [],
			from_warehouse: '',
			to_warehouse: '',
		}
)

const itemList = ref<string[]>([])
const bomList = ref<string[]>([])
const warehouseList = ref<string[]>([])

onMounted(async () => {
	store.$patch(state => state.cache.mappers['repack'] = stockEntry.value)
	await loadItems()
	await loadBOMs()
	await loadWarehouses()
})

const loadItems = async () => {
	const itemsData = await store.getAll<{ name: string }[]>('Item')
	itemList.value = itemsData.map(item => item.name)
}

const loadBOMs = async () => {
	const boms = await store.getAll<{ name: string }[]>('BOM')
	bomList.value = boms.map(bom => bom.name)
}

const loadWarehouses = async () => {
	const warehouses = await store.getAll<{ name: string }[]>('Warehouse', {
		filters: JSON.stringify([['is_group', '!=', '1']]),
	})
	warehouseList.value = warehouses.map(warehouse => warehouse.name)
}

const clearField = (field: 'from_warehouse' | 'to_warehouse') => {
	stockEntry.value[field] = ''
}

const update = () => {
	// TODO
}

const create = async () => {
	const body: StockEntry = {
		stock_entry_type: 'Repack',
		items: stockEntry.value.items || [],
		from_warehouse: stockEntry.value.from_warehouse,
		to_warehouse: stockEntry.value.to_warehouse,
		name: stockEntry.value.name,
	}
	let res = await store.insert<StockEntry>('Stock Entry', body)
	if (res?.data?.name) {
		stockEntry.value.name = res.data.name
	}
}

const repack = async () => {
	const res = await store.submit<StockEntry>('Stock Entry', stockEntry.value.name || '')
	if (res?.data) {
		store.$patch(state => {
			state.cache.mappers['repack'] = {
				name: '',
				stock_entry_type: 'Repack',
				items: [],
				from_warehouse: '',
				to_warehouse: '',
			}
		})
	}
}

watch(
	() => store.cache.mappers['repack']?.items,
	newItems => {
		items.value = (newItems || []).map(s => ({
			...s,
			label: s.item_code,
			count: { count: s.qty },
		}))
		componentKey.value++
	},
	{ immediate: true, deep: true }
)
const controlButtons = computed((): ControlButton[] => {
	if (!stockEntry.value.items.length || !stockEntry.value.from_warehouse || !stockEntry.value.to_warehouse) return []
	return [
		{ label: 'SAVE', color: { background: '#4791FF', text: 'var(--sc-btn-color)' }, action: create },
		{ label: 'REPACK', disabled: !stockEntry.value.name, color: { background: 'var(--sc-success)', text: 'var(--sc-btn-color)' }, action: repack },
	]
})
</script>
