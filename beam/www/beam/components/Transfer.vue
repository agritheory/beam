<template>
	<ControlButtons
		:doctypeName="stockEntryId"
		:onCreate="create"
		:onSubmit="() => store.submit<StockEntry>('Stock Entry', stockEntryId)"
		:onCancel="() => store.cancel<StockEntry>('Stock Entry', stockEntryId)"
	/>

	<ListView :items="listItems" :key="componentKey" />
</template>

<script setup lang="ts">
import { ref } from 'vue'

import { useDataStore } from '@/store'
import type { ListViewItem, StockEntry } from '@/types'
import ControlButtons from '../components/ControlButtons.vue'

const { id: sourceId } = defineProps<{ id: string }>()

const store = useDataStore()

const listItems = ref<ListViewItem[]>([])
const stockEntryId = ref('')
const componentKey = ref(0)

store.$subscribe((mutation, state) => {
	const parentfield = state.form.doctype === 'Work Order' ? 'required_items' : 'items'
	if (parentfield && state.form[parentfield]) {
		listItems.value = []
		state.form[parentfield].forEach(item => {
			item.wip_warehouse = state.form.wip_warehouse
			listItems.value.push({
				label: item.item_name,
				description: `${item.source_warehouse} > ${item.wip_warehouse}`,
				count: {
					count: item.transferred_qty,
					of: item.required_qty,
				},
			})
		})
		componentKey.value++
	}
})

const create = async () => {
	// TODO: check if source document is a different doctype
	const stockEntry = await store.getMappedStockEntry({
		work_order_id: sourceId,
		purpose: 'Material Transfer for Manufacture',
	})

	const { data, exception, response } = await store.insert('Stock Entry', stockEntry)
	if (data.name) {
		stockEntryId.value = data.name
	}
	return { data, exception, response }
}
</script>
