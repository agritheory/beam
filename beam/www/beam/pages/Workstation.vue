<template>
	<Navbar @click="handlePrimaryAction">
		<template #title>
			<h1>Workstations</h1>
		</template>
		<template #navbaraction>
			<RouterLink :to="{ name: 'demand' }">Done</RouterLink>
		</template>
	</Navbar>

	<ListView :items="workstations" />
</template>

<script setup lang="ts">
import type { ListViewItem } from '@stonecrop/beam'
import { onMounted, ref } from 'vue'

import { useBeamStore } from '@/stores/beam'
import type { Workstation } from '@/types'

const store = useBeamStore()
const workstations = ref<Partial<ListViewItem>[]>([])

onMounted(async () => {
	const stations = await store.getAll<Workstation[]>('Workstation', {
		fields: JSON.stringify(['name', 'workstation_type', 'plant_floor']),
		order_by: 'creation asc',
	})

	workstations.value = stations.map(row => {
		return {
			...row,
			// count: { count: row.produced_qty, of: row.qty },
			label: row.name,
			linkComponent: 'ListAnchor',
			route: `#/workstation/${row.name}`,
		}
	})
})

const handlePrimaryAction = () => {}
</script>
