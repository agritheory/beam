<template>
	<Navbar>
		<template #title>
			<h1 class="nav-title">Demand</h1>
		</template>
		<template #navbaraction><RouterLink route="#/home">HOME</RouterLink></template>
	</Navbar>
	<ListView :items="transfer" />
</template>

<script setup lang="ts">
import { Navbar } from '@stonecrop/beam'
import { onMounted, ref } from 'vue'

import { useDataStore } from '../store'
import type { ListViewItem } from '../types'

declare const frappe: any

const store = useDataStore()
const transfer = ref<Partial<ListViewItem>[]>([])

onMounted(async () => {
	const { data } = await store.getDemand({ order_by: 'creation asc' })

	// TODO: move this to the server
	data.forEach(row => {
		row.count = { count: row.allocated_qty, of: `${row.total_required_qty} ${row.stock_uom}` }
		row.label = `${row.item_code} from ${row.warehouse}`
		row.linkComponent = 'ListAnchor'
		row.description = row.parent
		row.route = `#/${frappe.scrub(row.doctype)}/${row.parent}`
		transfer.value.push(row)
	})
})

// const handlePrimaryAction = () => {}
</script>

<style scoped>
@import url('@stonecrop/beam/styles');
</style>
