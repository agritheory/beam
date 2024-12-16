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
			<BeamBtn class="clear-button" @click="clearField('sourceWarehouse')">
				&times;
			</BeamBtn>
		</div>
		<div class="dropdown-container">
			<ADropdown label="Target Warehouse" :items="warehouseList" v-model="targetWarehouse" />
			<BeamBtn class="clear-button" @click="clearField('targetWarehouse')">
				&times;
			</BeamBtn>
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
type Warehouse = {
	name: string,
}

const store = useBeamStore()

const stockEntryId = ref('')
const initialStockEntry = store.cache.mappers[stockEntryId.value] as StockEntry

const items = ref<ListViewItem[]>([])
const stockEntry = ref<StockEntry>({ ...initialStockEntry, stock_entry_type: 'Material Transfer' })
const componentKey = ref(0)

const warehouseList = ref<string[]>([])
const sourceWarehouse = ref('')
const targetWarehouse = ref('')

onMounted(async () => {
	store.form as Partial<StockEntry>
	await loadWarehouses()
	window.addEventListener('moveScan', handleScanned)
})

const handleScanned = async (event: CustomEvent) => {
	try {
		const scannedData = event.detail[0].context.doc.name
		console.log('scannedData', event.detail[0])
		
		if (!sourceWarehouse.value) {
			sourceWarehouse.value = scannedData
		} else if (!targetWarehouse.value) {
			targetWarehouse.value = scannedData
		} else {
			const barCode = event.detail[0].context.barcode
			console.log('barCode', barCode)

			const item_code = 'Pie Tin'

			const existingItem = items.value.find(item => item.item_code === item_code)

			if (existingItem) {
				existingItem.qty += 1
				existingItem.count.count += 1
			} else {
				items.value.push({
					item_code: item_code,
					label: item_code,
					count: { count: 1 },
					qty: 1,
					s_warehouse: sourceWarehouse.value,
					t_warehouse: targetWarehouse.value,
				})
			}
		}
	} catch (err) {
		console.log('Hubo un error al escanear', err)
	}
}

const loadWarehouses = async () => {
	const warehouses = await store.getAll<Warehouse[]>('Warehouse')
	warehouseList.value = warehouses.map(warehouse => warehouse.name)
}

const clearField = (field: 'sourceWarehouse' | 'targetWarehouse') => {
	if (field === 'sourceWarehouse') {
		sourceWarehouse.value = ''
	} else if (field === 'targetWarehouse') {
		targetWarehouse.value = ''
	}
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