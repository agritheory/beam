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
import { onMounted, ref } from 'vue'
import { Navbar } from '@stonecrop/beam'
import type { Workstation } from '../types'

const handlePrimaryAction = () => {}
// const workstations = ['Manufacture', 'Receive', 'Repack', 'Ship']
const workstations = ref<Partial<Workstation>[]>([])

onMounted(async () => {
	const params = new URLSearchParams({
		fields: JSON.stringify(['name', 'workstation_type', 'plant_floor']),
		order_by: 'creation asc',
	})

	const url = new URL(`/api/resource/Workstation?${params}`, window.location.origin)
	const response = await fetch(url)
	let { data }: { data: Partial<Workstation>[] } = await response.json()
	data.forEach(row => {
		// row.count = { count: row.produced_qty, of: row.qty }
		row.label = row.name
		row.linkComponent = 'ListAnchor'
		row.route = `#/workstation/${row.name}`
	})
	workstations.value = data
})
</script>
<style scoped>
@import url('@stonecrop/beam/styles');
</style>
