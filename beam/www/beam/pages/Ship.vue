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
import { ref } from 'vue'
import { useInfiniteScroll } from '@vueuse/core'
import { useDataStore } from '@/store'
import type { ListViewItem } from '@/types'

const store = useDataStore()
const items = ref<Partial<ListViewItem>[]>([])
const canLoadMore = ref(true)
const page = ref(1)

useInfiniteScroll(
	window,
	async () => {
		const { data } = await store.getDemand({ workstation: 'Shipping', page: page.value })
		if (data.length === 0) {
			canLoadMore.value = false
			return
		}

		// TODO: move this to the server
		data.forEach(row => {
			row.count = { count: row.allocated_qty, of: `${row.total_required_qty}` }
			row.label = `${row.doctype} - ${row.parent}`
			row.linkComponent = 'ListAnchor'
			row.description = `
				Item: ${row.item_code}
				Warehouse: ${row.warehouse}
				${row.customer ?? `Customer: ${row.customer}`}
			`.trim()
			row.route = `#/Delivery Note/new-delivery-note` // or draft delivery note if it exists
			items.value.push(row)
		})

		page.value++
	},
	{ canLoadMore: () => canLoadMore.value }
)

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
