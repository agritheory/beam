<template>
	<Navbar>
		<template #title>
			<h1 class="nav-title">Move</h1>
		</template>
		<template #navbaraction>
			<RouterLink :to="{ name: 'home' }">Home</RouterLink>
		</template>
	</Navbar>
	<div>
		<div class="dropdown-container">
			<ADropdown label="Source Warehouse" :items="warehouseList" v-model="sourceWarehouse" />
			<BeamBtn class="clear-button" @click="clearField('sourceWarehouse')"> &times; </BeamBtn>
		</div>
		<div class="dropdown-container">
			<ADropdown label="Target Warehouse" :items="warehouseList" v-model="targetWarehouse" />
			<BeamBtn class="clear-button" @click="clearField('targetWarehouse')"> &times; </BeamBtn>
		</div>
	</div>

	<!-- body section -->
	<ListView :items="items" :key="componentKey" />
	<div class="begin" v-if="items.length == 0">
		<span>Scan to Begin</span>
	</div>
	<!-- footer section -->
	<ControlButtons :buttons="controlButtons" />
</template>

<script setup lang="ts">
import type { ListViewItem } from '@stonecrop/beam'
import { ref, onMounted, computed } from 'vue'

import ControlButtons from '@/components/ControlButtons.vue'
import ADropdown from '@/components/ADropdown.vue'
import { useBeamStore } from '@/stores/beam'
import type { ControlButton, StockEntry } from '@/types'
import { watch } from 'vue'
type Warehouse = {
	name: string
}

const store = useBeamStore()

const stockEntryId = ref('')

const items = ref<ListViewItem[]>([])

const sourceWarehouse = computed(() => {
	return store.cache.mappers[stockEntryId.value]?.s_warehouse
})
const targetWarehouse = computed(() => {
	return store.cache.mappers[stockEntryId.value]?.t_warehouse
})

const stockEntry = ref<StockEntry>({ stock_entry_type: 'Material Transfer', items: [] })
const componentKey = ref(0)

const warehouseList = ref<string[]>([])

onMounted(async () => {
	store.form as Partial<StockEntry>
	await loadWarehouses()
	store.$patch(state => {
		state.cache.mappers[stockEntryId.value] = stockEntry.value
	})
})

const loadWarehouses = async () => {
	const warehouses = await store.getAll<Warehouse[]>('Warehouse')
	warehouseList.value = warehouses.map(warehouse => warehouse.name)
}

const clearField = (field: 'sourceWarehouse' | 'targetWarehouse') => {
	store.$patch(state => {
		const mapper = state.cache.mappers[stockEntryId.value]
		if (mapper) {
			if (field === 'sourceWarehouse') {
				mapper.s_warehouse = ''
			} else if (field === 'targetWarehouse') {
				mapper.t_warehouse = ''
			}
		}
	})
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
	console.log(stockEntry.value)
	console.log(items.value)
	return
	const { data, response } = await store.insert<StockEntry>('Stock Entry', stockEntry.value)
	if (data.name) {
		stockEntryId.value = data.name
	}
	return { data, response }
}

const controlButtons = computed((): ControlButton[] => {
	// if (!stockEntry.value) return []

	// const form = stockEntry.value as StockEntry
	// if (!form.items) return []

	return [
		{
			label: 'SAVE',
			disabled: items.value.length === 0,
			color: { background: '#4791FF', text: 'var(--sc-btn-color)' },
			action: create,
		},
		// {
		// 	label: 'SHIP',
		// 	disabled: form.items.length === 0 || !form.name,
		// 	hidden: Boolean(form.__islocal) || form.docstatus !== 0,
		// 	color: { background: 'var(--sc-success)', text: 'var(--sc-btn-color)' },
		// 	action: async () => await store.submit<StockEntry>('Stock Entry', form.name),
		// },
		// {
		// 	label: 'CANCEL',
		// 	disabled: form.items.length === 0 || !form.name,
		// 	hidden: Boolean(form.__islocal) || form.docstatus !== 1,
		// 	color: { background: 'var(--sc-alert)', text: 'var(--sc-btn-color)' },
		// 	action: async () => await store.cancel<StockEntry>('Stock Entry', form.name),
		// },
	]
})

watch(
	() => store.cache.mappers[stockEntryId.value]?.items,
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
.begin {
	width: 100%;
	text-align: center;
	font-size: 150%;
}

.dropdown-container {
	display: flex;
	align-items: baseline;
	position: relative;
	margin-top: 1rem;
}

.dropdown-container {
	display: flex;
	align-items: center;
	justify-content: center;
	position: relative;
	gap: 8px;
}
</style>
