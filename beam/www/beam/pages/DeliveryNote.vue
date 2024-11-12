<template>
	<Navbar>
		<template #title>
			<h1 class="nav-title">Delivery Note</h1>
		</template>
		<template #navbaraction>
			<RouterLink :to="{ name: 'home' }">Home</RouterLink>
		</template>
	</Navbar>
	<div class="box" v-show="list.length">
		<ListView :items="list" />
	</div>
	<ControlButtons
		:onCreate="create"
		:onSubmit="() => store.submit<ParentDoctype>('Stock Entry', deliveryNoteId)"
		:onCancel="() => store.cancel<ParentDoctype>('Stock Entry', deliveryNoteId)" />
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

import ControlButtons from '@/components/ControlButtons.vue'
import { useDataStore } from '@/store'
import type { DeliveryNote, ListViewItem, ParentDoctype } from '@/types'

const store = useDataStore()
const list = ref<ListViewItem[]>([])

onMounted(async () => {
	store.form as Partial<DeliveryNote>
	// console.log(JSON.stringify(store.form))
})

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
