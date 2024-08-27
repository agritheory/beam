<template>
	<!-- <Navbar @click="handlePrimaryAction">
		<template #title>
			<h3 class="nav-title">Transfer</h3>
		</template>
		<template #navbaraction>Done</template>
	</Navbar> -->
	<ListView :items="transfer" />
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Navbar } from '@stonecrop/beam'
import type { ListViewItem } from '../types'

const handlePrimaryAction = () => {}
let transfer = ref<Partial<ListViewItem>[]>([])
let transfers = []

onMounted(async () => {
	const params = new URLSearchParams({
		fields: JSON.stringify(['name', 'workstation_type', 'plant_floor']),
		order_by: 'creation asc',
	})

	const url = new URL(`/api/method/beam.beam.demand.demand.get_demand`, window.location.origin) // incorporate params
	const response = await fetch(url)
	let data = await response.json()
	// TODO: move this the server
	data.message.forEach(row => {
		row.count = { count: row.allocated_qty, of: `${row.total_required_qty} ${row.stock_uom}` }
		row.label = row.parent
		row.linkComponent = 'ListAnchor'
		row.description = `${row.item_code} - ${row.warehouse}`
		row.route = `#/${row.doctype}/${row.parent}`
		transfers.push(row)
	})
	transfer.value = transfers
})
</script>
<style scoped>
@import url('@stonecrop/beam/styles');
</style>
