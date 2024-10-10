<template>
	<Navbar @click="handlePrimaryAction">
		<template #title>
			<h1 class="nav-title">Move</h1>
		</template>
		<template #navbaraction>
			<RouterLink :to="{ name: 'home' }">Home</RouterLink>
		</template>
	</Navbar>
	<Transfer :id="stockEntry.name" />
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute } from 'vue-router'

import Transfer from '@/components/Transfer.vue'
import type { ListViewItem, StockEntry } from '@/types'

const route = useRoute()
const stockEntryId = route.params.id
const items = ref<ListViewItem[]>([])
const stockEntry = ref<Partial<StockEntry>>({})

const handlePrimaryAction = () => {
	console.log('handle primary action')
}
</script>
