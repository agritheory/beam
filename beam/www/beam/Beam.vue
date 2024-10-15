<template>
	<!-- setup modal behaviour -->
	<BeamModal @confirmmodal="confirmModal" @closemodal="closeModal" :showModal="showModal">
		<Confirm @confirmmodal="confirmModal" @closemodal="closeModal" />
	</BeamModal>
	<BeamModalOutlet @confirmmodal="confirmModal" @closemodal="closeModal"></BeamModalOutlet>

	<!-- setup scan input listeners -->
	<ScanInput :scanHandler="scan" @scanInstance="registerInstance" />

	<!-- setup main view -->
	<RouterView />
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { useScan } from '@/scan'

const { scanHandler } = useScan()
const showModal = ref(false)

onMounted(async () => {
	// TODO: (Frappe) implement actual server endpoint
	// TODO: (Mirage) mock new server endpoint in mirage
	// const response = await fetch('/mirage/workstations')
	// const data: Workstation[] = await response.json()
	// activeWorkstations.value = data.filter(workstation => workstation.status === 'Production')
	// inactiveWorkstations.value = data.filter(workstation => workstation.status === 'Off')
})

// const handlePrimaryAction = () => {
// 	showModal.value = true
// }

const scan = async (barcode: string, qty: number) => {
	await scanHandler.scan(barcode, qty)
}

const registerInstance = (instance: any) => {
	window.scanner = instance
}

const closeModal = () => {
	showModal.value = false
}

const confirmModal = () => {
	showModal.value = false
}
</script>

<style>
@import url('@stonecrop/beam/styles');
.navbar-action a {
	color: inherit;
	text-decoration: none;
}
.navbar-action a:visited {
	color: inherit;
	text-decoration: none;
}
.navbar-action a:hover {
	color: inherit;
	text-decoration: none;
}
.navbar-action a:active {
	color: inherit;
	text-decoration: none;
}
</style>
