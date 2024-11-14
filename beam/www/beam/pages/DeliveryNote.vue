<template>
	<Navbar>
		<template #title>
			<h1 class="nav-title">Delivery Note</h1>
			<span v-if="store.form.dirty" class="nav-subtitle" )>Unsaved changes</span>
		</template>
		<template #navbaraction>
			<RouterLink :to="{ name: 'home' }">Home</RouterLink>
		</template>
	</Navbar>
	<div class="box" v-show="items.length">
		<ListView :items="items" />
	</div>
	<ControlButtons :buttons="controlButtons" />
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'

import ControlButtons from '@/components/ControlButtons.vue'
import { useBeamStore } from '@/stores/beam'
import type { DeliveryNote, ListViewItem, ParentDoctype } from '@/types'

const store = useBeamStore()
const items = ref<ListViewItem[]>([])

onMounted(async () => {
	store.form as Partial<DeliveryNote>
	// console.log(JSON.stringify(store.form))
})

const create = async () => {
	// TODO: implement create
	const deliveryNote = store.form as Partial<DeliveryNote>
	const { data, exception, response } = await store.insert('Delivery Note', deliveryNote)
	return { data, exception, response }
}

const controlButtons = computed(() => {
	if (!store.form) {
		return []
	}
	return [
		{
			label: 'SAVE',
			action: create,
			disabled: items.value.length === 0,
			color: { background: '#4791FF', text: 'var(--sc-btn-color)' },
		},
		{
			label: 'SHIP',
			action: () => store.submit<DeliveryNote>('Delivery Note', store.form),
			disabled: store.form.items.length === 0 || !store.form.name,
			color: { background: 'var(--sc-success)', text: 'var(--sc-btn-color)' },
		},
		{
			label: 'CANCEL',
			action: () => store.cancel<DeliveryNote>('Delivery Note', store.form),
			disabled: store.form.items.length === 0 || !store.form.name,
			hidden: store.form.docstatus != 1,
			color: { background: 'var(--sc-alert)', text: 'var(--sc-btn-color)' },
		},
	]
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
.dirty {
	color: tomato;
	font-weight: 700;
}
</style>
