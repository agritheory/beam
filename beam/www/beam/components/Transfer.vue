<template>
	<div class="control-buttons">
		<button @click="create" :disabled="!!stockEntryId">Save</button>
		<button @click="store.submit<StockEntry>('Stock Entry', stockEntryId)" :disabled="!stockEntryId">Submit</button>
		<button @click="store.cancel<StockEntry>('Stock Entry', stockEntryId)" :disabled="!stockEntryId">Cancel</button>
	</div>

	<ListView :items="listItems" />
</template>

<script setup lang="ts">
import { ref, watchEffect } from 'vue'

import { useDataStore } from '../store'
import type { ListViewItem, StockEntry, WorkOrderItem } from '../types'

const props = defineProps<{
	id: string
	items: WorkOrderItem[]
}>()

const store = useDataStore()

const listItems = ref<ListViewItem[]>([])
const stockEntryId = ref('')

const create = async () => {
	const response = await store.createStockEntry({
		work_order_id: props.id,
		purpose: 'Material Transfer for Manufacture',
	})

	const { message: doc } = await response.json()
	if (!doc) {
		alert('error')
		return
	}

	const { data, response: insertResponse } = await store.insert<StockEntry>('Stock Entry', doc)
	if (insertResponse.ok) {
		stockEntryId.value = data.name
	} else {
		alert('error')
	}
}

watchEffect(() => {
	listItems.value = props.items?.map(it => ({
		label: it.item_name,
		description: `${it.source_warehouse} > ${it.wip_warehouse}`,
		count: {
			count: it.transferred_qty,
			of: it.required_qty,
		},
	}))
})
</script>

<style scoped>
.control-buttons {
	display: flex;
	justify-content: flex-end;
	gap: 1rem;
}
</style>
