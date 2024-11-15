<template>
	<!-- navigation section -->
	<Navbar>
		<template #title>
			<h1 class="nav-title">Purchase Receipt</h1>
			<span v-if="store.form.dirty" class="dirty">Unsaved</span>
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
import type { ControlButton, ListViewItem, PurchaseReceipt } from '@/types'

const store = useBeamStore()
const items = ref<ListViewItem[]>([])

onMounted(async () => {
	store.form as Partial<PurchaseReceipt>
})

store.$subscribe((mutation, state) => {
	const parentfield = state.form.doctype === 'Work Order' ? 'required_items' : 'items'
	if (parentfield && state.form[parentfield]) {
		items.value = []
		state.form[parentfield].forEach(item => {
			item.wip_warehouse = state.form.wip_warehouse
			items.value.push({
				label: item.item_name,
				description: `${item.warehouse}`,
				count: {
					count: item.received_qty,
					of: item.qty,
				},
			})
		})
	}
})

const create = async () => {
	if (store.form.dirty) {
		const document: PurchaseReceipt = { ...store.form }
		document.items = document.items.filter(item => item.qty > 0)
		const response = await store.insert('Purchase Receipt', document)

		if (!response.exception) {
			store.$patch(state => {
				state.form.dirty = false
				state.cache.mappers[workOrderId] = response.data
				stockEntry.value = response.data
			})
		}

		return response
	} else {
		// TODO: a few options here:
		// 1. allow setting a condition in ControlButtons to control when to enable the button
		// 2. add a toast message here telling the user why this is a no-op
	}
}

const controlButtons = computed((): ControlButton[] => {
	if (!store.form) return []

	const form = store.form as PurchaseReceipt
	if (!form.items) return []

	return [
		{
			label: 'SAVE',
			disabled: items.value.length === 0,
			color: { background: '#4791FF', text: 'var(--sc-btn-color)' },
			action: create,
		},
		{
			label: 'RECEIVE',
			disabled: form.items.length === 0 || !form.name,
			color: { background: 'var(--sc-success)', text: 'var(--sc-btn-color)' },
			action: () => store.submit<PurchaseReceipt>('Purchase Receipt', form.name),
		},
		{
			label: 'CANCEL',
			disabled: form.items.length === 0 || !form.name,
			hidden: form.docstatus != 1,
			color: { background: 'var(--sc-alert)', text: 'var(--sc-btn-color)' },
			action: () => store.cancel<PurchaseReceipt>('Purchase Receipt', form.name),
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
