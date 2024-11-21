<template>
	<!-- navigation section -->
	<Navbar>
		<template #title>
			<h1 class="nav-title">Ship</h1>
		</template>
		<template #navbaraction>
			<RouterLink :to="{ name: 'home' }">Home</RouterLink>
		</template>
	</Navbar>

	<!-- body section -->
	<ListView :items="ship" />
</template>

<script setup lang="ts">
import { useInfiniteScroll } from '@vueuse/core'
import { ref } from 'vue'

import { useBeamStore } from '@/stores/beam'
import type { ListViewItem } from '@/types'

const store = useBeamStore()
const ship = ref<Partial<ListViewItem>[]>([])
const canLoadMore = ref(true)
const page = ref(1)

useInfiniteScroll(
	window,
	async () => {
		const { data } = await store.getDemand({ filters: JSON.stringify({ doctype: 'Sales Order' }), page: page.value })
		if (data.length === 0) {
			canLoadMore.value = false
			return
		}

		data.forEach(row => {
			row.count = { count: row.allocated_qty, of: `${row.total_required_qty}` }
			row.label = `${row.doctype} - ${row.parent}`
			row.linkComponent = 'ListAnchor'
			row.description = `
				Item: ${row.item_code}
				Warehouse: ${row.warehouse}
				${row.customer ?? `Customer: ${row.customer}`}
			`.trim()
			row.route = `#/delivery-note?id=${row.parent}`
			ship.value.push(row)
		})

		page.value++
	},
	{ canLoadMore: () => canLoadMore.value }
)
</script>
