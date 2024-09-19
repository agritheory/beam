<template>
	<Navbar @click="handlePrimaryAction">
		<template #title>
			<h1 class="nav-title">Ship</h1>
		</template>
		<template #navbaraction>Home</template>
	</Navbar>
	<ListView :items="items" />
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { useFetchDemand } from '../fetch'
import type { ListViewItem } from '../types'

// const handlePrimaryAction = () => {}
const items = ref<Partial<ListViewItem>[]>([])

onMounted(async () => {
	const { data } = await useFetchDemand({ workstation: 'Shipping' })

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
</script>

<style>
@import url('@stonecrop/beam/styles');
</style>
