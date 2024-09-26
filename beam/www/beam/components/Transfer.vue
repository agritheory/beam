<template>
	<div>
		<ControlButtons
			:onCreate="create"
			:onSubmit="() => store.submit<StockEntry>('Stock Entry', stockEntryId)"
			:onCancel="() => store.cancel<StockEntry>('Stock Entry', stockEntryId)"
		/>

		<ListView :items="listItems" />
	</div>
</template>

<script setup lang="ts">
import { ref, watchEffect } from 'vue'

import { useDataStore } from '@/store'
import type { ListViewItem, StockEntry, WorkOrderItem } from '@/types'
import ControlButtons from '../components/ControlButtons.vue'

const { id, items } = defineProps<{
	id: string
	items: WorkOrderItem[]
}>()

const store = useDataStore()

const listItems = ref<ListViewItem[]>([])
const stockEntryId = ref('')

const create = async () => {
	const stockEntry = await store.getMappedStockEntry({
		work_order_id: id,
		purpose: 'Material Transfer for Manufacture',
	})

	const { data, exception, response } = await store.insert('Stock Entry', stockEntry)
	if (data.name) {
		stockEntryId.value = data.name
	}
	return { data, exception, response }
}

watchEffect(() => {
	listItems.value = items?.map(it => ({
		label: it.item_name,
		description: `${it.source_warehouse} > ${it.wip_warehouse}`,
		count: {
			count: it.transferred_qty,
			of: it.required_qty,
		},
	}))
})
</script>
