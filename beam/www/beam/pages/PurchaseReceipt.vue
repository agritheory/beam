<template>
	<!-- navigation section -->
	<Navbar>
		<template #title>
			<h1>Purchase Receipt</h1>
			<span v-if="purchaseReceipt?.dirty" class="dirty">Unsaved</span>
		</template>
		<template #navbaraction>
			<RouterLink :to="{ name: 'home' }">Home</RouterLink>
		</template>
	</Navbar>

	<!-- body section -->
	<div class="box" v-show="items.length">
		<ListView :items="items" :key="refreshKey" @update="handleItemUpdate" />
	</div>

	<!-- footer section -->
	<ControlButtons :buttons="controlButtons" />
</template>

<script setup lang="ts">
import type { ListViewItem } from '@stonecrop/beam'
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'

import ControlButtons from '@/components/ControlButtons.vue'
import { useBeamStore } from '@/stores/beam'
import type { ControlButton, PurchaseReceipt, PurchaseReceiptItem } from '@/types'

const route = useRoute()
const store = useBeamStore()
const refreshKey = ref(0)

const purchaseOrderId = computed(() => route.params.id?.toString() || 'new-purchase-receipt')

const purchaseReceipt = computed(() => store.cache.mappers[purchaseOrderId.value] as PurchaseReceipt | undefined)

const handleItemUpdate = (updatedItem: PurchaseReceiptItem & ListViewItem) => {
	const doc = purchaseReceipt.value
	if (!doc?.items) return

	const itemIndex = doc.items.findIndex(item => item.item_code === updatedItem.item_code)

	if (itemIndex !== -1) {
		if (updatedItem.count?.count !== undefined) {
			doc.items[itemIndex].received_qty = updatedItem.count.count
		}

		doc.dirty = true
	}
}

// hack: since array reactivity is not present in Vue 3, force-refresh the listviews on store update
store.$subscribe(mutation => {
	if (['patch function', 'patch object'].includes(mutation.type)) {
		refreshKey.value++
	}
})

const items = computed((): (PurchaseReceiptItem & ListViewItem)[] => {
	if (!purchaseReceipt.value?.items) return []

	return purchaseReceipt.value.items.map(item => {
		return {
			...item,
			label: item.item_name,
			description: `${item.warehouse}`,
			count: {
				count: item.received_qty,
				of: item.qty,
			},
		}
	})
})

const create = async () => {
	const doc = purchaseReceipt.value
	if (!doc?.dirty) {
		return
	}

	const document: PurchaseReceipt = { ...doc }
	document.items = document.items.filter(item => item.received_qty > 0)
	for (const item of document.items) {
		item.qty = item.received_qty
	}
	const { data, response } = await store.insert('Purchase Receipt', document)

	if (response.ok && data) {
		if (store.camera.pendingPhotos.length > 0) {
			await store.uploadFiles('Purchase Receipt', data.name || '', store.camera.pendingPhotos)
			store.clearPendingPhotos()
		}

		store.$patch(state => {
			state.cache.mappers[purchaseOrderId.value] = data
			data.dirty = false
		})
	}
}

const controlButtons = computed((): ControlButton[] => {
	const form = purchaseReceipt.value
	if (!form?.items) return []

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
			hidden: Boolean(form.__islocal) || form.docstatus !== 0,
			color: { background: 'var(--sc-success)', text: 'var(--sc-btn-color)' },
			action: async () => await store.submit<PurchaseReceipt>('Purchase Receipt', form.name),
		},
		{
			label: 'CANCEL',
			disabled: form.items.length === 0 || !form.name,
			hidden: Boolean(form.__islocal) || form.docstatus !== 1,
			color: { background: 'var(--sc-alert)', text: 'var(--sc-btn-color)' },
			action: async () => await store.cancel<PurchaseReceipt>('Purchase Receipt', form.name),
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
