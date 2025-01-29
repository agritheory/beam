<template>
	<Navbar>
		<template #title>
			<h1 class="nav-title">Move</h1>
		</template>
		<template #navbaraction>
			<RouterLink :to="{ name: 'home' }">Home</RouterLink>
		</template>
	</Navbar>
	<div class="move">
		<div class="dropdown-container">
			<ADropdown label="Source Warehouse" :items="warehouseList" v-model="stockEntry.from_warehouse" />
			<BeamBtn class="clear-button" @click="clearField('from_warehouse')"> X </BeamBtn>
		</div>
		<div class="dropdown-container">
			<ADropdown label="Target Warehouse" :items="warehouseList" v-model="stockEntry.to_warehouse" />
			<BeamBtn class="clear-button" @click="clearField('to_warehouse')"> X </BeamBtn>
		</div>
	</div>

	<!-- body section -->
	<ListView :items="items" :key="componentKey" @update="update" />
	<div class="begin" v-if="items.length == 0">
		<span>Scan Items and Scan or Select Warehouses to Begin</span>
	</div>
	<!-- footer section -->
	<ControlButtons :buttons="controlButtons" />
</template>

<script setup lang="ts">
import type { ListViewItem } from '@stonecrop/beam'
import { ref, onMounted, computed } from 'vue'

import ControlButtons from '@/components/ControlButtons.vue'
import { useBeamStore } from '@/stores/beam'
import type { ControlButton, DocActionResponse, StockEntry } from '@/types'
import { watch } from 'vue'
type Warehouse = {
	name: string
}

const store = useBeamStore()
const items = ref<ListViewItem[]>([])
const stockEntry = computed(
	(): StockEntry =>
		(store.cache.mappers[''] as StockEntry) || {
			name: '',
			stock_entry_type: 'Material Transfer',
			items: [],
			from_warehouse: '',
			to_warehouse: '',
		}
)
const componentKey = ref(0)

const warehouseList = ref<string[]>([])

onMounted(async () => {
	store.form as Partial<StockEntry>
	store.$patch(state => {
		state.cache.mappers[''] = stockEntry.value
	})
	await loadWarehouses()
})

const loadWarehouses = async () => {
	const warehouses = await store.getAll<Warehouse[]>('Warehouse', {
		filters: JSON.stringify([['is_group', '!=', '1']]),
	})
	warehouseList.value = warehouses.map(warehouse => warehouse.name)
}

const clearField = (field: 'from_warehouse' | 'to_warehouse') => {
	store.$patch(state => {
		const mapper = state.cache.mappers['']
		if (mapper) mapper[field] = ''
	})
}

const update = () => {
	// TODO
}

// store.$subscribe((mutation, state) => {
// 	const parentfield = state.form.doctype === 'Work Order' ? 'required_items' : 'items'
// 	if (parentfield && state.form[parentfield]) {
// 		items.value = []
// 		state.form[parentfield].forEach(item => {
// 			item.wip_warehouse = state.form.wip_warehouse
// 			items.value.push({
// 				label: item.item_name,
// 				description: `${item.source_warehouse} > ${item.wip_warehouse}`,
// 				count: {
// 					count: item.transferred_qty,
// 					of: item.required_qty,
// 				},
// 			})
// 		})
// 		componentKey.value++
// 	}
// })

const create = async () => {
	const body: StockEntry = {
		stock_entry_type: 'Material Transfer',
		items: stockEntry.value.items.map(i => ({
			...i,
			s_warehouse: stockEntry.value.from_warehouse,
			t_warehouse: stockEntry.value.to_warehouse,
		})),
		name: stockEntry.value.name,
	}
	let res: DocActionResponse<StockEntry>

	if (body.name) {
		res = await store.update<StockEntry>('Stock Entry', body.name, body)
	} else {
		res = await store.insert<StockEntry>('Stock Entry', body)
	}
	const { data, response } = res
	if (data.name) {
		stockEntry.value.name = data.name
	}
	return { data, response }
}

const move = async () => {
	const res = await store.submit<StockEntry>('Stock Entry', stockEntry.value.name)
	if (res?.data)
		store.$patch(state => {
			state.cache.mappers[''] = {
				name: '',
				stock_entry_type: 'Material Transfer',
				items: [],
				from_warehouse: '',
				to_warehouse: '',
			}
		})
}

const controlButtons = computed((): ControlButton[] => {
	if (!stockEntry.value.items.length || !stockEntry.value.from_warehouse || !stockEntry.value.to_warehouse) return []
	return [
		{
			label: 'SAVE',
			disabled: items.value.length === 0,
			color: { background: '#4791FF', text: 'var(--sc-btn-color)' },
			action: create,
		},
		{
			label: 'MOVE',
			disabled: !stockEntry.value.name,
			hidden: !stockEntry.value.name,
			color: { background: 'var(--sc-success)', text: 'var(--sc-btn-color)' },
			action: move,
		},
	]
})

watch(
	() => store.cache.mappers['']?.items,
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
</script>

<style>
.move {
	margin-bottom: 1.5em;
}

.move .autocomplete input,
.autocomplete-results {
	font-size: 150%;
}

.autocomplete-results {
	padding-inline: 3px !important;
}

.move .input-wrapper label {
	margin: calc(-2.5rem - calc(2.15rem / 2)) 0 0 1ch !important;
}

.clear-button {
	margin-bottom: 2px;
	padding: 0.9rem 1rem !important;
}

.begin {
	width: 100%;
	text-align: center;
	font-size: 150%;
	text-wrap: balance;
}

.dropdown-container {
	display: flex;
	align-items: flex-end !important;
	justify-content: center;
	position: relative;
	margin-top: 1rem;
	gap: 8px;
}
</style>
