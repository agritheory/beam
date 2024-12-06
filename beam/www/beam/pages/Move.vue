<template>
	<Navbar>
		<template #title>
			<h1 class="nav-title">Move</h1>
		</template>
		<template #navbaraction>
			<RouterLink :to="{ name: 'home' }">Home</RouterLink>
		</template>
	</Navbar>
	{{ console.log(store.scanner.config) }}
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

	<ListView :items="listItems" :key="componentKey" />
	<div class="begin" v-if="listItems.length === 0">
		<span>Scan to Begin</span>
	</div>

	<ControlButtons :buttons="controlButtons" />
</template>


<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'

import ControlButtons from '@/components/ControlButtons.vue'
import ADropdown from '@/components/ADropdown.vue'
import { useBeamStore } from '@/stores/beam'
import type { ControlButton, ListViewItem, StockEntry } from '@/types'
type Warehouse = {
	name: string,
}

const store = useBeamStore()
const listItems = ref<ListViewItem[]>([])
const componentKey = ref(0)

const warehouseList = ref<string[]>([])
const sourceWarehouse = ref('')
const targetWarehouse = ref('')

onMounted(async () => {
	store.form as Partial<StockEntry>
	await loadWarehouses()
	window.addEventListener('moveScan', handleScanned)
})

const handleScanned = (event: CustomEvent) => {
	const scannedData = event.detail[0].context.doc.name
	if (!sourceWarehouse.value) {
		sourceWarehouse.value = scannedData
	} else if (!targetWarehouse.value) {
		targetWarehouse.value = scannedData
	}
	/* 
	TODO: else > fill listItems
	*/
	console.log('Warehouse scanned:', scannedData)
}

const controlButtons = computed((): ControlButton[] => {
	// TODO
	return []
})

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
</script>

<style>
/* @import url('@stonecrop/aform/styles'); */
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