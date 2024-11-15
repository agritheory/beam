<template>
	<!-- navigation section -->
	<Navbar>
		<template #title>
			<h1 class="nav-title">Delivery Note</h1>
			<span v-if="store.form.dirty" class="nav-subtitle">Unsaved changes</span>
		</template>
		<template #navbaraction>
			<RouterLink :to="{ name: 'home' }">Home</RouterLink>
		</template>
	</Navbar>

	<!-- body section -->
	<div class="box" v-show="items.length">
		<ListView :items="items" />
	</div>

	<!-- footer section -->
	<ControlButtons :buttons="controlButtons" />
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'

import ControlButtons from '@/components/ControlButtons.vue'
import { useBeamStore } from '@/stores/beam'
import type { ControlButton, DeliveryNote, ListViewItem } from '@/types'

const store = useBeamStore()
const items = ref<ListViewItem[]>([])

onMounted(async () => {
	store.form as Partial<DeliveryNote>
})

const controlButtons = computed((): ControlButton[] => {
	if (!store.form) return []

	const form = store.form as DeliveryNote
	return [
		{
			label: 'SAVE',
			disabled: items.value.length === 0,
			color: { background: '#4791FF', text: 'var(--sc-btn-color)' },
			action: async () => {
				// TODO: implement create
				const deliveryNote = store.form as Partial<DeliveryNote>
				return await store.insert('Delivery Note', deliveryNote)
			},
		},
		{
			label: 'SHIP',
			disabled: form.items.length === 0 || !form.name,
			color: { background: 'var(--sc-success)', text: 'var(--sc-btn-color)' },
			action: () => store.submit<DeliveryNote>('Delivery Note', form.name),
		},
		{
			label: 'CANCEL',
			disabled: form.items.length === 0 || !form.name,
			hidden: form.docstatus != 1,
			color: { background: 'var(--sc-alert)', text: 'var(--sc-btn-color)' },
			action: () => store.cancel<DeliveryNote>('Delivery Note', form.name),
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
