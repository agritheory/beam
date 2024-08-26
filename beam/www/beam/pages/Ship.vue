<template>
	<ListView :items="items" />
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { Navbar } from '@stonecrop/beam'
import type { ListViewItem } from '../types'

const handlePrimaryAction = () => {}
let items = ref<Partial<ListViewItem>[]>([])
let shipping = []

onMounted(async () => {
	const params = new URLSearchParams({
		workstation: 'Shipping',
	})

	const url = new URL(`/api/method/beam.beam.demand.demand.get_demand?` + params.toString(), window.location.origin)
	const response = await fetch(url)
	let data = await response.json()
	// TODO: move this the server
	data.message.forEach(row => {
		row.count = { count: row.allocated_qty, of: `${row.total_required_qty}` }
		row.label = `${row.doctype} - ${row.parent}`
		row.linkComponent = 'ListAnchor'
		row.description = `${row.item_code} - ${row.warehouse}`
		row.route = `#/${row.doctype}/${row.parent}`
		shipping.push(row)
	})
	items.value = shipping
})
</script>
<style>
@import url('@stonecrop/beam/styles');
</style>
