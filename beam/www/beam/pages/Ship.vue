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
import type { ListViewItem } from '@stonecrop/beam'
import { useInfiniteScroll } from '@vueuse/core'
import { ref } from 'vue'

import { useBeamStore } from '@/stores/beam'

const store = useBeamStore()
const ship = ref<ListViewItem[]>([])
const canLoadMore = ref(true)
const page = ref(1)
const dates = ref<string[]>([])

useInfiniteScroll(
	window,
	async () => {
		const { data } = await store.getDemand({ filters: JSON.stringify({ doctype: 'Sales Order' }), page: page.value })
		if (data.length === 0) {
			canLoadMore.value = false
			return
		}

		for (const row of data) {
			const scheduledDate = new Date(row.delivery_date)

			// add day-divider config when date changes
			if (!dates.value.includes(scheduledDate.toDateString())) {
				dates.value.push(scheduledDate.toDateString())
				ship.value.push({
					date: scheduledDate.toISOString(),
					linkComponent: 'BeamDayDivider',
				})
			}

			ship.value.push({
				count: { count: row.allocated_qty, of: row.total_required_qty },
				label: `${row.doctype} - ${row.parent}`,
				linkComponent: 'ListAnchor',
				description: `
					Item: ${row.item_code}
					Warehouse: ${row.warehouse}
					${row.customer ?? `Customer: ${row.customer}`}
				`.trim(),
				route: `#/delivery-note?id=${row.parent}`,
			})
		}

		page.value++
	},
	{ canLoadMore: () => canLoadMore.value }
)
</script>
