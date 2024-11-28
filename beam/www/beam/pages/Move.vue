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
import { useBeamStore } from '@/stores/beam'
import type { ControlButton, StockEntry } from '@/types'

const store = useBeamStore()

const items = ref<ListViewItem[]>([])
const stockEntryId = ref('')
const stockEntry = ref(store.cache.mappers[stockEntryId.value] as StockEntry)
const componentKey = ref(0)

onMounted(async () => {
	store.form as Partial<StockEntry>
})

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

// const create = async () => {
// 	const stockEntry = await store.getMappedStockEntry({
// 		work_order_id: sourceId,
// 		purpose: 'Material Transfer for Manufacture',
// 	})

// 	const { data, response } = await store.insert('Stock Entry', stockEntry)
// 	if (data.name) {
// 		stockEntryId.value = data.name
// 	}
// 	return { data, response }
// }

const controlButtons = computed((): ControlButton[] => {
	if (!stockEntry.value) return []

	const form = stockEntry.value as StockEntry
	if (!form.items) return []

	return [
		// {
		// 	label: 'SAVE',
		// 	disabled: items.value.length === 0,
		// 	color: { background: '#4791FF', text: 'var(--sc-btn-color)' },
		// 	action: create,
		// },
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

<style scoped>
.begin {
	width: 100%;
	text-align: center;
	font-size: 150%;
}
</style>
