<template>
	<Navbar>
		<template #title>
			<h1>Demand</h1>
		</template>
		<template #navbaraction>
			<RouterLink :to="{ name: 'home' }">Home</RouterLink>
		</template>
	</Navbar>

	<ListView :items="transfer" />
</template>

<script setup lang="ts">
import type { ListViewItem } from '@stonecrop/beam'
import { useInfiniteScroll } from '@vueuse/core'
import { ref } from 'vue'

import { useBeamStore } from '@/stores/beam'

declare const frappe: any

const store = useBeamStore()
const transfer = ref<ListViewItem[]>([])
const canLoadMore = ref(true)
const page = ref(1)
const dates = ref<string[]>([])

useInfiniteScroll(
	window,
	async () => {
		const { data } = await store.getDemand({ order_by: 'creation asc', page: page.value })
		if (!data || data.length === 0) {
			canLoadMore.value = false
			return
		}

		// TODO: move this to the server
		for (const row of data) {
			const scheduledDate = new Date(row.allocated_date)

			// add day-divider config when date changes
			if (!dates.value.includes(scheduledDate.toDateString())) {
				dates.value.push(scheduledDate.toDateString())
				transfer.value.push({
					date: scheduledDate.toISOString(),
					linkComponent: 'BeamDayDivider',
				})
			}

			transfer.value.push({
				label: `${row.item_code} from ${row.item_warehouse}`,
				linkComponent: 'ListAnchor',
				route: `#/${frappe.scrub(row.doctype)}/${row.parent}`,
				description: `
					[${row.parent}]
					Production Item: ${row.production_item}
					BOM No: ${row.bom_no}
				`.trim(),
				count: {
					count: +row.allocated_qty.toFixed(2),
					of: +row.total_required_qty.toFixed(2),
				},
			})
		}

		page.value++
	},
	{ canLoadMore: () => canLoadMore.value }
)
</script>
