<template>
	<BeamModal @confirmmodal="confirmModal" @closemodal="closeModal" :showModal="showModal">
		<Confirm @confirmmodal="confirmModal" @closemodal="closeModal" />
	</BeamModal>

	<Navbar @click="handlePrimaryAction">
		<template #title> </template>
		<template #navbaraction>Done</template>
	</Navbar>

	<ListView :items="items" />
	<ActionFooter @click="handlePrimaryAction">Done</ActionFooter>
	<ScanInput @scaninput="handleScanInput($event)" />
	<BeamModalOutlet @confirmmodal="confirmModal" @closemodal="closeModal"></BeamModalOutlet>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import type { Workstation } from './types'

const activeWorkstations = ref<Workstation[]>([])
const inactiveWorkstations = ref<Workstation[]>([])

const showModal = ref(false)

const handleScanInput = (barcode: string) => {
	incrementListItemCountByBarcode(barcode)
}

let items = ref([])

const handlePrimaryAction = () => {
	showModal.value = true
}

const incrementListItemCountByBarcode = (barcode?: string) => {
	if (!barcode) {
		return
	}

	const detectedItemsByIndex = items
		.map((item, index) => {
			return item.barcode === barcode ? index : undefined
		}) // return indices of matching barcode
		.filter(x => x !== undefined) // remove undefined

	for (const [detectedIndex, rowIndex] of detectedItemsByIndex.entries()) {
		if (rowIndex) {
			if (detectedIndex !== detectedItemsByIndex.length - 1) {
				if (items[rowIndex].count.count < items[rowIndex].count.of) {
					// don't overcount if its not the last row of that barcode
					let incrementedValue = items[rowIndex].count.count + 1
					items[rowIndex].count.count = incrementedValue
					break
				} else {
					continue
				}
			} else {
				// set it in the last item anyway
				let incrementedValue = items[rowIndex].count.count + 1
				items[rowIndex].count.count = incrementedValue
				break
			}
		}
	}
}

const closeModal = () => {
	showModal.value = false
}

const confirmModal = () => {
	showModal.value = false
}

onMounted(async () => {
	// TODO: (Frappe) implement actual server endpoint
	// TODO: (Mirage) mock new server endpoint in mirage
	// const response = await fetch('/mirage/workstations')
	// console.log(response)
	// const data: Workstation[] = await response.json()
	// console.log(data) //JSON.stringify(data))
	// activeWorkstations.value = data.filter(workstation => workstation.status === 'Production')
	// inactiveWorkstations.value = data.filter(workstation => workstation.status === 'Off')
})
</script>

<style scoped>
@import url('@stonecrop/beam/styles');
</style>
