<template>
	<Navbar>
		<template #title>
			<h1 class="nav-title">Receive</h1>
		</template>
		<template #navbaraction>
			<RouterLink :to="{ name: 'home' }">Home</RouterLink>
		</template>
	</Navbar>

	<ListView :items="transfer" />
</template>

<script setup lang="ts">
import { Navbar } from '@stonecrop/beam'
import { useInfiniteScroll } from '@vueuse/core'
import { ref } from 'vue'

import { useDataStore } from '@/store'
import type { ListViewItem } from '@/types'

declare const frappe: any

const store = useDataStore()
const transfer = ref<Partial<ListViewItem>[]>([])
const canLoadMore = ref(true)
const page = ref(1)

useInfiniteScroll(
	window,
	async () => {
		const { data } = await store.getReceiving({ order_by: 'creation asc', page: page.value })
		if (data.length === 0) {
			canLoadMore.value = false
			return
		}

		// TODO: move this to the server
		data.forEach(row => {
			row.count = { count: row.received_qty, of: `${row.stock_qty}` }
			row.label = `${row.item_code} from ${row.warehouse}`
			row.linkComponent = 'ListAnchor'
			row.description = row.parent
			row.route = `#/${frappe.scrub(row.doctype)}/${row.parent}`
			transfer.value.push(row)
		})

		page.value++
	},
	{ canLoadMore: () => canLoadMore.value }
)

// const handlePrimaryAction = () => {}
</script>

<style scoped>
@import url('@stonecrop/beam/styles');
</style>
