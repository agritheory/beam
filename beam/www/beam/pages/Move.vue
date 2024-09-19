<template>
	<Navbar @click="handlePrimaryAction">
		<template #title>
			<h1 class="nav-title">Move</h1>
		</template>
		<template #navbaraction>Home</template>
	</Navbar>
	<Transfer :items="stockEntry?.items" :id="stockEntry.name" />
</template>
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import type { StockEntry } from '../types'
import { useFetch } from '../fetch'
import Transfer from '../components/Transfer.vue'

const route = useRoute()
const stockEntryId = route.params.id
const items = ref<ListViewItem[]>([])
let stockEntry = ref<Partial<StockEntry>>({})
</script>
