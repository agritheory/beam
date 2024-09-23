<template>
	<Navbar @click="handlePrimaryAction">
		<template #title>
			<h1 class="nav-title">Workstations</h1>
		</template>
		<template #navbaraction>Done</template>
	</Navbar>
	<ListView :items="workstations" />
</template>

<script setup lang="ts">
import { Navbar } from '@stonecrop/beam'
import { onMounted, ref } from 'vue'

import { useDataStore } from '@/store'
import type { ListViewItem, Workstation } from '@/types'

const store = useDataStore()
const workstations = ref<ListViewItem[]>([])

onMounted(async () => {
	const stations = await store.getAll<Workstation[]>('Workstation', {
		fields: JSON.stringify(['name', 'workstation_type', 'plant_floor']),
		order_by: 'creation asc',
	})

	stations.forEach(row => {
		workstations.value.push({
			...row,
			// count: { count: row.produced_qty, of: row.qty },
			label: row.name,
			linkComponent: 'ListAnchor',
			route: `#/workstation/${row.name}`,
		})
	})
})

const handlePrimaryAction = () => {}
</script>

<style scoped>
@import url('@stonecrop/beam/styles');
</style>
