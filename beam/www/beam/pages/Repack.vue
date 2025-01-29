<template>
	<Navbar @click="handlePrimaryAction">
		<template #title>
			<h1>Repack</h1>
		</template>
		<template #navbaraction>
			<RouterLink :to="{ name: 'home' }">Home</RouterLink>
		</template>
	</Navbar>

	<!-- <scale>
		<readout :mqtt="" />
	</scale> -->
</template>

<script setup lang="ts">
import type { ListViewItem } from '@stonecrop/beam'
import { ref } from 'vue'
import { useRoute } from 'vue-router'

import type { StockEntry } from '@/types'

const route = useRoute()
const stockEntryId = route.params.id
const items = ref<ListViewItem[]>([])
const stockEntry = ref<Partial<StockEntry>>({})

const handlePrimaryAction = () => {
	throw new Error('Not implemented')
}
</script>
