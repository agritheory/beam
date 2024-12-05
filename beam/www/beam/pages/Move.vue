<template>
	<!-- navigation section -->
	<Navbar>
		<template #title>
			<h1 class="nav-title">Move</h1>
		</template>
		<template #navbaraction>
			<RouterLink :to="{ name: 'home' }">Home</RouterLink>
		</template>
	</Navbar>
	<div>
		<ADropdown
			label="Source Warehouse"
			:items="warehouseList"
			v-model="sourceWarehouse"
			@filterChanged="filterChanged"
		/>
		<ADropdown
			label="Target Warehouse"
			:items="warehouseList"
			v-model="targetWarehouse"
			@filterChanged="filterChanged"
		/>
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
})

const controlButtons = computed((): ControlButton[] => {
	return []
})

const filterChanged = async (query: string) => {
	console.log(`onChange: ${query}`)
}

const loadWarehouses = async () => {
	const warehouses = await store.getAll<Warehouse[]>('Warehouse')
	warehouseList.value = warehouses.map(warehouse => warehouse.name)
}

const onScan = (scannedValue: string) => {
	if (!sourceWarehouse.value) {
		sourceWarehouse.value = scannedValue
	} else if (!targetWarehouse.value) {
		targetWarehouse.value = scannedValue
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
</style>