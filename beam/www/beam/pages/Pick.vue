<template>
	<Navbar>
		<template #title>
			<h1>Pick</h1>
		</template>
		<template #navbaraction>
			<RouterLink :to="{ name: 'home' }">Home</RouterLink>
		</template>
	</Navbar>

	<ScanOutput v-show="store.scanner.config.show_scan_output" />

	<ListView :items="items" :key="listKey" />
</template>

<script setup lang="ts">
import type { ListViewItem } from '@stonecrop/beam'
import { onMounted, ref } from 'vue'

import ScanOutput from '@/components/ScanOutput.vue'
import { useBeamStore } from '@/stores/beam'

type PickListRow = {
	name: string
	purpose?: string
	work_order?: string
	customer?: string
	modified?: string
	status?: string
}

const store = useBeamStore()
const items = ref<ListViewItem[]>([])
const listKey = ref(0)

const loadPickLists = async () => {
	const rows = await store.getAll<PickListRow[]>('Pick List', {
		filters: JSON.stringify({ docstatus: 0, status: ['!=', 'Cancelled'] }),
		fields: JSON.stringify(['name', 'purpose', 'work_order', 'customer', 'modified', 'status']),
		order_by: 'modified desc',
		limit_page_length: 50,
	})

	items.value = rows.map(row => {
		const context = row.work_order
			? `Work Order: ${row.work_order}`
			: row.customer
			  ? `Customer: ${row.customer}`
			  : row.purpose || ''
		return {
			barcode: row.name,
			label: row.name,
			description: [context, row.status].filter(Boolean).join(' · '),
			linkComponent: 'ListAnchor',
			route: `#/pick-list/${row.name}`,
		}
	})
	listKey.value++
}

onMounted(loadPickLists)
</script>
