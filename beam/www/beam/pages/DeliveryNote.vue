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
		:onSubmit="() => store.submit<ParentDoctype>('Stock Entry', deliveryNoteId)"
		:onCancel="() => store.cancel<ParentDoctype>('Stock Entry', deliveryNoteId)" />
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRoute } from 'vue-router'

import ControlButtons from '@/components/ControlButtons.vue'
import { useDataStore } from '@/store'
import type { ListViewItem, ParentDoctype } from '@/types'

const route = useRoute()
const store = useDataStore()
const deliveryNoteId = route.params.orderId.toString()
const items = ref<ListViewItem[]>([])

const create = async () => {
	// TODO: implement create
	const deliveryNote = store.form as Partial<ParentDoctype>
	const { data, exception, response } = await store.insert('Delivery Note', deliveryNote)
	return { data, exception, response }
}
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
