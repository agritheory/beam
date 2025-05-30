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
import type { ControlButton, StockReconciliation } from '@/types'

const store = useBeamStore()
const items = ref([])
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

const warehouseList = ref<string[]>([])

onMounted(async () => {
	store.$patch(state => (state.cache.mappers['stock-reconciliation'] = reconciliation.value))
	warehouseList.value = store.warehouseList.filter(w => !w.is_group).map(w => w.name)
})

const clearField = () => store.$patch(state => (state.cache.mappers['stock-reconciliation']['set_warehouse'] = ''))

const loadItems = async warehouse => {
	try {
		const response = await store.getStockReconciliationItems(warehouse)
		if (!response || response.length === 0) return
		items.value = response.map(item => ({
			...item,
			label: item.item_code,
			count: { count: item.qty },
			description: item.stock_uom,
		}))
	} catch (error) {
		console.error('Error loading items:', error)
	}
}

const controlButtons = computed((): ControlButton[] => [])

watch(
	() => reconciliation.value.set_warehouse,
	warehouse => {
		if (!warehouse) return
		loadItems(warehouse)
	}
)
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
