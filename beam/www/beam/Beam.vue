<template>
	<!-- TODO: remove when beam interface is to be implemented -->
	<h1>Active Workstations:</h1>
	<p v-for="workstation in activeWorkstations" :key="workstation.name">
		{{ workstation.workstation_name }} (Capacity: {{ workstation.production_capacity }})
	</p>

	<h1>Inactive Workstations:</h1>
	<p v-for="workstation in inactiveWorkstations" :key="workstation.name">
		{{ workstation.workstation_name }} (Capacity: {{ workstation.production_capacity }})
	</p>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import type { Workstation } from './types'

const activeWorkstations = ref<Workstation[]>([])
const inactiveWorkstations = ref<Workstation[]>([])

onMounted(async () => {
	// TODO: (Frappe) implement actual server endpoint
	// TODO: (Mirage) mock new server endpoint in mirage
	const response = await fetch('/api/workstations')
	const data: Workstation[] = await response.json()

	activeWorkstations.value = data.filter(workstation => workstation.status === 'Production')
	inactiveWorkstations.value = data.filter(workstation => workstation.status === 'Off')
})
</script>

<style scoped></style>
