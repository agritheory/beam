<template>
	<!-- navigation section -->
	<Navbar>
		<template #title>
			<h1 class="nav-title">Receive</h1>
		</template>
		<template #navbaraction>
			<RouterLink :to="{ name: 'home' }">Home</RouterLink>
		</template>
	</Navbar>

	<!-- body section -->
	<ListView :items="receive" />
</template>

<script setup lang="ts">
import type { ListViewItem } from '@stonecrop/beam'
import { useInfiniteScroll } from '@vueuse/core'
import { ref } from 'vue'

import { useBeamStore } from '@/stores/beam'

const store = useBeamStore()
const receive = ref<ListViewItem[]>([])
const canLoadMore = ref(true)
const page = ref(1)
const dates = ref<string[]>([])

useInfiniteScroll(
	window,
	async () => {
		const { data } = await store.getReceiving({ order_by: 'creation asc', page: page.value })
		if (data.length === 0) {
			canLoadMore.value = false
			return
		}

		// TODO: move this to the server
		for (const row of data) {
			const scheduledDate = new Date(row.schedule_date)

			// add day-divider config when date changes
			if (!dates.value.includes(scheduledDate.toDateString())) {
				dates.value.push(scheduledDate.toDateString())
				receive.value.push({
					date: scheduledDate.toISOString(),
					linkComponent: 'BeamDayDivider',
				})
			}

			receive.value.push({
				count: { count: row.received_qty, of: row.stock_qty },
				label: `${row.item_code} from ${row.warehouse}`,
				linkComponent: 'ListAnchor',
				description: `
					[${row.parent}]
					Warehouse: ${row.warehouse}
					Supplier: ${row.supplier}
				`.trim(),
				route: `#/purchase_order/${row.parent || 'new-purchase-order'}`,
			})
		}

		page.value++
	},
	{ canLoadMore: () => canLoadMore.value }
)
</script>

<style>
@import url('@stonecrop/beam/styles');

.beam_list-text label,
.beam_list-text p {
	white-space: pre-line !important;
}
</style>
