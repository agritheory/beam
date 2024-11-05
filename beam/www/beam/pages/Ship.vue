<template>
	<Navbar @click="handlePrimaryAction">
		<template #title>
			<h1 class="nav-title">Ship</h1>
		</template>
		<template #navbaraction>
			<RouterLink :to="{ name: 'home' }">Home</RouterLink>
		</template>
	</Navbar>
	<ListView :items="items" />
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { useDataStore } from '@/store'
import type { ListViewItem } from '@/types'

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
		row.route = `#/Delivery Note/new-delivery-note` // or draft delivery note if it exists
		items.value.push(row)
	})
})

function newDeliveryNote(so) {
	// match save and name API
	// return document name
	return so // not correct
}

const handlePrimaryAction = () => {}
</script>

<style>
@import url('@stonecrop/beam/styles');
</style>
