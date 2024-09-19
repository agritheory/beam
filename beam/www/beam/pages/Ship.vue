<template>
	<ListView :items="items" />
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { useDataStore } from '../store'
import type { ListViewItem } from '../types'

const store = useDataStore()
const items = ref<Partial<ListViewItem>[]>([])

onMounted(async () => {
	const { data } = await store.getDemand({ workstation: 'Shipping' })

	// TODO: move this to the server
	data.forEach(row => {
		row.count = { count: row.allocated_qty, of: row.total_required_qty }
		row.label = `${row.doctype} - ${row.parent}`
		row.linkComponent = 'ListAnchor'
		row.description = `${row.item_code} - ${row.warehouse}`
		row.route = `#/${row.doctype}/${row.parent}`
		items.value.push(row)
	})
})

// const handlePrimaryAction = () => {}
</script>

<style>
@import url('@stonecrop/beam/styles');
</style>
