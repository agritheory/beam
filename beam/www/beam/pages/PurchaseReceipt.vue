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

	<Camera :allowPreview="true" @photos-captured="handlePhotosCaptured" />
	{{ console.log({items}) }}
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
import Camera from '@/components/Camera.vue'
import { useBeamStore } from '@/stores/beam'
import type { ControlButton, PurchaseReceipt, PurchaseReceiptItem } from '@/types'

const route = useRoute()
const store = useBeamStore()
const purchaseOrderId = route.params.id?.toString() || 'new-purchase-receipt'

console.log('Initializing with purchaseOrderId:', purchaseOrderId)
console.log('Store cache.mappers keys:', Object.keys(store.cache.mappers))
console.log('Full store.cache.mappers:', store.cache.mappers)

const purchaseReceipt = ref(store.cache.mappers[purchaseOrderId] as PurchaseReceipt)
const refreshKey = ref(0)
const capturedFiles = ref<File[]>([])

console.log('purchaseReceipt.value:', purchaseReceipt.value)
console.log('purchaseReceipt.value?.items:', purchaseReceipt.value?.items)
console.log('purchaseReceipt.value?.items length:', purchaseReceipt.value?.items?.length)

const handlePhotosCaptured = (photos: File[]) => {
	capturedFiles.value = photos
}

const handleItemUpdate = (updatedItem: PurchaseReceiptItem & ListViewItem) => {
	const itemIndex = purchaseReceipt.value.items.findIndex(item => item.item_code === updatedItem.item_code)

	if (itemIndex !== -1) {
		if (updatedItem.count?.count !== undefined) {
			purchaseReceipt.value.items[itemIndex].received_qty = updatedItem.count.count
		}

		purchaseReceipt.value.dirty = true
	}
}

// hack: since array reactivity is not present in Vue 3, force-refresh the listviews on store update
store.$subscribe(mutation => {
	console.log('Store mutation:', mutation.type, mutation)
	if (['patch function', 'patch object'].includes(mutation.type)) {
		console.log('Refreshing ListView, new refreshKey:', refreshKey.value + 1)
		refreshKey.value++
	}
})

const items = computed((): (PurchaseReceiptItem & ListViewItem)[] => {
	console.log('items computed - purchaseReceipt.value:', purchaseReceipt.value)
	console.log('items computed - purchaseReceipt.value?.items:', purchaseReceipt.value?.items)
	
	if (!purchaseReceipt.value) {
		console.error('items computed - purchaseReceipt.value is null/undefined!')
		return []
	}
	
	if (!purchaseReceipt.value.items) {
		console.error('items computed - purchaseReceipt.value.items is null/undefined!')
		console.log('items computed - Full purchaseReceipt object:', JSON.stringify(purchaseReceipt.value, null, 2))
		return []
	}
	
	if (!Array.isArray(purchaseReceipt.value.items)) {
		console.error('items computed - purchaseReceipt.value.items is not an array!', typeof purchaseReceipt.value.items)
		return []
	}
	
	const mappedItems = purchaseReceipt.value.items.map(item => {
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
	
	console.log('items computed - mapped items count:', mappedItems.length)
	console.log('items computed - mapped items:', mappedItems)
	
	return mappedItems
})

const create = async () => {
	console.log('create() called')
	console.log('create() - purchaseReceipt.value:', purchaseReceipt.value)
	console.log('create() - purchaseReceipt.value.dirty:', purchaseReceipt.value?.dirty)
	
	if (purchaseReceipt.value.dirty) {
		const document: PurchaseReceipt = { ...purchaseReceipt.value }
		console.log('create() - document before filter:', document)
		document.items = document.items.filter(item => item.received_qty > 0)
		console.log('create() - document.items after filter:', document.items)
		for (const item of document.items) {
			item.qty = item.received_qty
		}
		console.log('create() - Calling store.insert with document:', document)
		const { data, response } = await store.insert('Purchase Receipt', document)

		console.log('create() - Response:', { ok: response.ok, status: response.status, data })
		
		if (response.ok && data) {
			console.log('create() - Success! Data received:', data)
			if (capturedFiles.value.length > 0) {
				console.log('create() - Uploading files:', capturedFiles.value.length)
				await store.uploadFiles('Purchase Receipt', data.name || '', capturedFiles.value)
			}

			store.$patch(() => {
				purchaseReceipt.value = data
				purchaseReceipt.value.dirty = false
				console.log('create() - Updated purchaseReceipt.value:', purchaseReceipt.value)
			})
		} else {
			console.error('create() - Failed!', { ok: response.ok, status: response.status, data })
		}
	} else {
		console.log('create() - Not dirty, skipping save')
		// TODO: a few options here:
		// 1. allow setting a condition in ControlButtons to control when to enable the button
		// 2. add a toast message here telling the user why this is a no-op
	}
}

const controlButtons = computed((): ControlButton[] => {
	console.log('controlButtons computed - purchaseReceipt.value:', purchaseReceipt.value)
	if (!purchaseReceipt.value) {
		console.log('controlButtons - No purchaseReceipt, returning empty array')
		return []
	}

	const form = purchaseReceipt.value as PurchaseReceipt
	if (!form.items) {
		console.log('controlButtons - No form.items, returning empty array')
		return []
	}

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
