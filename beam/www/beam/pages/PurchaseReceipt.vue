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
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import ControlButtons from '@/components/ControlButtons.vue'
import { useIncomingInspectionItemCodes } from '@/composables/useIncomingInspectionItemCodes'
import { useLineInspections } from '@/composables/useLineInspections'
import { useBeamStore } from '@/stores/beam'
import type { ControlButton, PurchaseReceipt, PurchaseReceiptItem } from '@/types'
import { disambiguateListLabels, itemListLine } from '@/utils/itemListLine'
import { applyInspectionLines, firstPendingGateInspection } from '@/utils/inspectionList'

const route = useRoute()
const router = useRouter()
const store = useBeamStore()
const refreshKey = ref(0)

const purchaseOrderId = computed(() => route.params.id?.toString() || 'new-purchase-receipt')

const purchaseReceipt = computed(() => store.cache.mappers[purchaseOrderId.value] as PurchaseReceipt | undefined)

const savedReceiptName = computed(() => {
	const prName = purchaseReceipt.value?.name
	if (!prName || prName.startsWith('new-')) return undefined
	return prName
})
const receiptLineItems = computed(() => purchaseReceipt.value?.items)

const { itemCodes: incomingInspectionItemCodes, reload: reloadIncomingInspectionCodes } =
	useIncomingInspectionItemCodes(receiptLineItems)

const { byRow, reload: reloadInspections } = useLineInspections(
	computed(() => 'Purchase Receipt'),
	savedReceiptName,
	receiptLineItems
)

const syncRouteToSavedReceipt = (prName: string) => {
	const routeId = route.params.id?.toString()
	if (!routeId || routeId === prName) return
	router.replace({ name: 'purchase-receipt', params: { id: prName } })
	store.$patch(state => {
		const doc = state.cache.mappers[routeId]
		if (doc) {
			state.cache.mappers[prName] = doc
			delete state.cache.mappers[routeId]
		}
	})
}

watch(
	() => purchaseReceipt.value?.name,
	name => {
		if (!name || name.startsWith('new-')) return
		syncRouteToSavedReceipt(name)
		reloadInspections()
		reloadIncomingInspectionCodes()
	}
)

watch([byRow, incomingInspectionItemCodes], () => {
	refreshKey.value++
})

const handleItemUpdate = (updatedItem: PurchaseReceiptItem & ListViewItem) => {
	const doc = purchaseReceipt.value
	if (!doc?.items) return

	const itemIndex = doc.items.findIndex(item =>
		updatedItem.name ? item.name === updatedItem.name : item.item_code === updatedItem.item_code
	)

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
		reloadInspections()
		reloadIncomingInspectionCodes()
	}
})

const items = computed((): (PurchaseReceiptItem & ListViewItem)[] => {
	if (!purchaseReceipt.value?.items) return []

	const mapped = disambiguateListLabels(
		purchaseReceipt.value.items.map(item => {
			const line = itemListLine(item)
			return {
				...item,
				label: line.label,
				description: line.description,
				barcode: item.name,
				count: {
					count: item.received_qty,
					of: item.qty,
				},
			}
		})
	)
	return applyInspectionLines(mapped, byRow.value, undefined, incomingInspectionItemCodes.value)
})

const pendingGateInspection = computed(() =>
	firstPendingGateInspection(
		purchaseReceipt.value?.name,
		byRow.value,
		purchaseReceipt.value?.items,
		incomingInspectionItemCodes.value
	)
)

const goToPendingInspection = async () => {
	const target = pendingGateInspection.value
	if (!target) return
	const from = `#/purchase-receipt/${encodeURIComponent(purchaseOrderId.value)}`
	await router.push({
		name: 'quality_inspection',
		params: {
			doctype: target.reference_type,
			name: target.reference_name,
			row: target.row,
		},
		query: {
			from,
			...(target.state ? { state: target.state } : {}),
		},
	})
}

const retryPendingPhotoUpload = async (docname: string) => {
	const result = await store.uploadFiles('Purchase Receipt', docname, store.camera.pendingPhotos)
	store.setPendingPhotos(result?.failed ?? [])
}

const create = async () => {
	const doc = purchaseReceipt.value

	if (!doc?.dirty) {
		if (doc?.name && store.camera.pendingPhotos.length > 0) {
			await retryPendingPhotoUpload(doc.name)
		}
		return
	}

	const document: PurchaseReceipt = { ...doc }
	document.items = document.items.filter(item => item.received_qty > 0)
	for (const item of document.items) {
		item.qty = item.received_qty
	}

	const isExisting = Boolean(document.name) && !document.__islocal && !String(document.name).startsWith('new-')
	const { data, response } = isExisting
		? await store.update<PurchaseReceipt>('Purchase Receipt', document.name!, document)
		: await store.insert('Purchase Receipt', document)

	if (response.ok && data) {
		if (data.name && store.camera.pendingPhotos.length > 0) {
			await retryPendingPhotoUpload(data.name)
		}

		const cacheKey = purchaseOrderId.value
		store.$patch(state => {
			state.cache.mappers[data.name!] = data
			if (cacheKey !== data.name) {
				delete state.cache.mappers[cacheKey]
			}
			data.dirty = false
		})
		if (data.name && route.params.id !== data.name) {
			await router.replace({ name: 'purchase-receipt', params: { id: data.name } })
		}
		await reloadInspections()
	}
}

const controlButtons = computed((): ControlButton[] => {
	const form = purchaseReceipt.value
	if (!form?.items) return []

	const receiveVisible = !Boolean(form.__islocal) && form.docstatus === 0
	const receiveDisabled = form.items.length === 0 || !form.name
	const receiveColor = { background: 'var(--sc-success)', text: 'var(--sc-btn-color)' }

	return [
		{
			label: 'SAVE',
			disabled: items.value.length === 0,
			action: create,
		},
		...(receiveVisible && pendingGateInspection.value
			? [
					{
						label: 'INSPECT',
						disabled: receiveDisabled,
						color: receiveColor,
						action: goToPendingInspection,
					},
			  ]
			: receiveVisible
			  ? [
						{
							label: 'SUBMIT',
							disabled: receiveDisabled,
							color: receiveColor,
							action: async () => await store.submit<PurchaseReceipt>('Purchase Receipt', form.name),
						},
			    ]
			  : []),
		{
			label: 'CANCEL',
			disabled: form.items.length === 0 || !form.name,
			hidden: Boolean(form.__islocal) || form.docstatus !== 1,
			color: { background: 'var(--sc-beam-danger-fill)', text: 'var(--sc-btn-color)' },
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
	border: 1px solid var(--sc-row-border-color);
	border-radius: 0;
	outline: 2px solid transparent;
	flex: 1;
	min-width: 100px;
}

.dirty {
	color: var(--sc-beam-danger-fill);
	font-weight: 700;
}
</style>
