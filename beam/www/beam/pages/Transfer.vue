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
// import { Navbar } from '@stonecrop/beam'
import { onMounted, ref } from 'vue'

import { useFetchDemand } from '../fetch'
import type { ListViewItem } from '../types'

// const handlePrimaryAction = () => {}
const transfer = ref<Partial<ListViewItem>[]>([])

onMounted(async () => {
	const { data } = await useFetchDemand({ order_by: 'creation asc' })

	// TODO: move this to the server
	data.forEach(row => {
		row.count = { count: row.allocated_qty, of: `${row.total_required_qty} ${row.stock_uom}` }
		row.label = row.parent
		row.linkComponent = 'ListAnchor'
		row.description = `${row.item_code} - ${row.warehouse}`
		row.route = `#/${frappe.scrub(row.doctype)}/${row.parent}`
		transfer.value.push(row)
	})
})
</script>

<style scoped>
@import url('@stonecrop/beam/styles');
</style>
