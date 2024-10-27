<template>
	<Navbar>
		<template #title>
			<h1 class="nav-title">Manufacture</h1>
		</template>
		<template #navbaraction>
			<RouterLink :to="{ name: 'home' }">Home</RouterLink>
		</template>
	</Navbar>
	<div class="box" v-show="items.length">
		<ListView :items="items" />
	</div>
	<ControlButtons
		:onCreate="create"
		:onSubmit="() => store.submit<StockEntry>('Stock Entry', stockEntryId)"
		:onCancel="() => store.cancel<StockEntry>('Stock Entry', stockEntryId)" />
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import ControlButtons from '@/components/ControlButtons.vue'
import { useDataStore } from '@/store'
import type { ListViewItem, DeliveryNote } from '@/types'

const route = useRoute()
const store = useDataStore()
const DeliveryNoteId = route.params.orderId.toString()
const items = ref<ListViewItem[]>([])

onMounted(async () => {
	const deliveryNote = store.form as Partial<DeliveryNote>
})
</script>

<style scoped>
b {
	display: flex;
	justify-content: center;
	align-items: center;
}

.container {
	display: flex;
	gap: 20px;
	/* Space between the boxes */
}

.box {
	padding: 2rem;
	margin: 0.5rem;
	font-size: 100%;
	border: 2px solid gray;
	outline: 2px solid transparent;
	flex: 1;
	min-width: 100px;
}
</style>
