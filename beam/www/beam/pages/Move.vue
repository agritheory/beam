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
	<ListView :items="listItems" :key="componentKey" />
	<div class="begin" v-if="listItems.length == 0">
		<span>Scan to Begin</span>
	</div>

	<!-- footer section -->
	<ControlButtons
		:onCreate="create"
		:onSubmit="() => store.submit<StockEntry>('Stock Entry', stockEntryId)"
		:onCancel="() => store.cancel<StockEntry>('Stock Entry', stockEntryId)" />
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

import ControlButtons from '@/components/ControlButtons.vue'
import { useBeamStore } from '@/stores/beam'
import type { ListViewItem, StockEntry } from '@/types'

const store = useBeamStore()

const listItems = ref<ListViewItem[]>([])
const stockEntryId = ref('')
const componentKey = ref(0)

onMounted(async () => {
	store.form as Partial<StockEntry>
})

// store.$subscribe((mutation, state) => {
// 	const parentfield = state.form.doctype === 'Work Order' ? 'required_items' : 'items'
// 	if (parentfield && state.form[parentfield]) {
// 		listItems.value = []
// 		state.form[parentfield].forEach(item => {
// 			item.wip_warehouse = state.form.wip_warehouse
// 			listItems.value.push({
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
	throw new Error('Not implemented')

	// const stockEntry = await store.getMappedStockEntry({
	// 	work_order_id: sourceId,
	// 	purpose: 'Material Transfer for Manufacture',
	// })

	// const { data, exception, response } = await store.insert('Stock Entry', stockEntry)
	// if (data.name) {
	// 	stockEntryId.value = data.name
	// }
	// return { data, exception, response }
}
</script>

<style scoped>
.begin {
	width: 100%;
	text-align: center;
	font-size: 150%;
}
</style>
