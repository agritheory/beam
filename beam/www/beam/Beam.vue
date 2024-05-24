<template>
	<!-- TODO: remove when beam interface is to be implemented -->
	<h1>Active Workstations:</h1>
	<p v-for="workstation in activeWorkstations" :key="workstation">
		{{ workstation.workstation_name }} (Capacity: {{ workstation.production_capacity }})
	</p>

	<h1>Inactive Workstations:</h1>
	<p v-for="workstation in inactiveWorkstations" :key="workstation">
		{{ workstation.workstation_name }} (Capacity: {{ workstation.production_capacity }})
	</p>
</template>

<script setup>
import { onMounted, ref } from 'vue'

const activeWorkstations = ref('')
const inactiveWorkstations = ref('')

onMounted(async () => {
	let headers = { 'X-Frappe-Site-Name': window.location.hostname }
	if (window.csrf_token) {
		headers['X-Frappe-CSRF-Token'] = window.csrf_token
	}
	const response = await fetch('/api/workstations', { headers })
	const data = await response.json()

	activeWorkstations.value = data.filter(d => d.status === 'Production')
	inactiveWorkstations.value = data.filter(d => d.status === 'Off')
})
</script>

<style scoped></style>
