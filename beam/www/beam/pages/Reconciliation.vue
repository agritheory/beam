<template>
	<Navbar>
		<template #title>
			<h1>Reconciliation</h1>
		</template>
		<template #navbaraction>
			<RouterLink :to="{ name: 'home' }">Home</RouterLink>
		</template>
	</Navbar>

	<div class="reconciliation">
		<div class="dropdown-container">
			<ADropdown label="Warehouse" :items="warehouseList" v-model="reconciliation.set_warehouse" />
			<BeamBtn class="clear-button" @click="clearField()"> X </BeamBtn>
		</div>
	</div>

	<!-- body section -->
	<ul v-if="items.length > 0" class="beam_list-view reconciliation-list" :key="componentKey">
		<ReconciliationListRow
			v-for="row in items"
			:key="`${row.item_code}-${row.count?.count ?? 'blank'}`"
			:item="row"
			@update="handleItemUpdate"
			@remove="removeRow(row.item_code)" />
	</ul>
	<div class="begin" v-else>
		<span>Scan or Select Warehouses to Begin</span>
	</div>

	<div v-if="showUncountedModal" class="reconciliation-modal-backdrop" role="dialog" aria-modal="true">
		<div class="reconciliation-modal">
			<p>{{ uncountedModalMessage }}</p>
			<div class="reconciliation-modal-actions">
				<BeamBtn @click="confirmSave('counted_only')">Save counted only</BeamBtn>
				<BeamBtn @click="confirmSave('include_zero_uncounted')">Set uncounted to zero</BeamBtn>
				<BeamBtn @click="showUncountedModal = false">Cancel</BeamBtn>
			</div>
		</div>
	</div>

	<!-- footer section -->
	<ControlButtons :buttons="controlButtons" />
</template>

<script setup lang="ts">
import type { ListViewItem } from '@stonecrop/beam'
import { ref, computed, onMounted, onUnmounted, watch, nextTick } from 'vue'

import ControlButtons from '@/components/ControlButtons.vue'
import ReconciliationListRow from '@/components/ReconciliationListRow.vue'
import { useBeamStore, type ReconciliationItemScanPayload } from '@/stores/beam'
import type { ControlButton, StockReconciliation, StockEntryItem } from '@/types'
import { useBeamToast } from '@/utils/toast'
import {
	buildReconciliationItems,
	hasCountedQuantity,
	type ReconciliationListRow as ReconciliationRow,
	type ReconciliationSaveMode,
	uncountedRowCount,
	warehouseRowFromApi,
} from '@/utils/reconciliation'

const store = useBeamStore()
const toast = useBeamToast()
const componentKey = ref(0)
const items = ref<ReconciliationRow[]>([])
const warehouseList = ref<string[]>([])
const showUncountedModal = ref(false)

const reconciliation = computed(
	(): StockReconciliation =>
		(store.cache.mappers['stock-reconciliation'] as StockReconciliation) || {
			name: '',
			purpose: 'Stock Reconciliation',
			items: [],
			set_warehouse: '',
		}
)

const uncountedModalMessage = computed(() => {
	const n = uncountedRowCount(items.value)
	return `${n} item${n === 1 ? '' : 's'} not counted. How should uncounted lines be saved?`
})

const blurActiveCountInput = () => {
	const active = document.activeElement
	if (active instanceof HTMLElement && active.closest('.beam_item-count')) {
		active.blur()
	}
}

const focusCountInput = (itemCode: string) => {
	nextTick(() => {
		for (const row of document.querySelectorAll('.reconciliation-list .reconciliation-list-row')) {
			const labelEl = row.querySelector('label.beam--bold')
			if (labelEl?.textContent?.trim() !== itemCode) continue

			const editable = row.querySelector('.beam_item-count span[contenteditable="true"]') as HTMLElement | null
			if (!editable) continue

			editable.focus()
			const range = document.createRange()
			range.selectNodeContents(editable)
			const selection = window.getSelection()
			selection?.removeAllRanges()
			selection?.addRange(range)
			break
		}
	})
}

const replaceRow = (index: number, row: ReconciliationRow) => {
	items.value.splice(index, 1, row)
}

const handleReconciliationScan = (payload: ReconciliationItemScanPayload) => {
	if (!payload.item_code) return

	blurActiveCountInput()

	const scanKeys = [payload.item_code, payload.item_name].filter(Boolean) as string[]
	const existingIndex = items.value.findIndex(item => {
		const rowKeys = [item.item_code, item.label, item.item_name].filter(Boolean) as string[]
		return scanKeys.some(key => rowKeys.includes(key))
	})

	if (existingIndex === -1) {
		items.value.push({
			item_code: payload.item_code,
			label: payload.item_code,
			warehouse: payload.warehouse || reconciliation.value.set_warehouse,
			stock_uom: payload.stock_uom,
			valuation_rate: payload.valuation_rate,
			count: {
				count: 1,
				uom: payload.stock_uom,
			},
			debounce: 1000,
		})
		focusCountInput(payload.item_code)
		return
	}

	const row = items.value[existingIndex]
	const countState = row.count
	if (!countState) return

	const previous = countState.count
	const nextCount = previous == null ? 1 : previous + 1
	const updatedRow = {
		...row,
		count: {
			...countState,
			count: nextCount,
		},
	}
	replaceRow(existingIndex, updatedRow)

	if (previous == null) {
		focusCountInput(updatedRow.label || updatedRow.item_code || payload.item_code)
	}
}

const handleItemUpdate = (updatedItem: ReconciliationRow & ListViewItem) => {
	const index = items.value.findIndex(item => item.item_code === updatedItem.item_code)
	if (index === -1) return
	items.value[index] = { ...items.value[index], ...updatedItem }
}

const removeRow = (itemCode: string) => {
	items.value = items.value.filter(item => item.item_code !== itemCode)
}

const clearField = () => {
	store.$patch(state => (state.cache.mappers['stock-reconciliation']['set_warehouse'] = ''))
	store.$patch(state => ((state.cache.mappers['stock-reconciliation'] as StockReconciliation).items = []))
	items.value = []
}

const resetItems = () => {
	store.$patch(state => ((state.cache.mappers['stock-reconciliation'] as StockReconciliation).items = []))
	items.value = []
}

let activeWarehouse = ''

const loadItemsFromWarehouse = async (warehouse: string) => {
	if (!warehouse) return
	activeWarehouse = warehouse
	try {
		const response = (await store.getStockReconciliationItems(warehouse)) as StockEntryItem[] | undefined
		if (warehouse !== activeWarehouse) return
		for (const apiItem of response || []) {
			if (items.value.some(item => item.item_code === apiItem.item_code)) continue
			items.value.push(warehouseRowFromApi(apiItem, warehouse))
		}
	} catch (error) {
		console.error('Error loading items:', error)
	}
}

const persist = async (mode: ReconciliationSaveMode) => {
	const warehouse = reconciliation.value.set_warehouse
	const body = {
		purpose: 'Stock Reconciliation' as const,
		set_warehouse: warehouse,
		items: buildReconciliationItems(items.value, warehouse, mode),
		name: reconciliation.value.name,
	}

	let res
	if (body.name) {
		res = await store.update('Stock Reconciliation', body.name, body)
	} else {
		res = await store.insert('Stock Reconciliation', body)
	}
	const { data } = res
	if (data && data.name) reconciliation.value.name = data.name
	return res
}

const trySave = async () => {
	if (!hasCountedQuantity(items.value)) {
		toast.error('Count at least one item before saving')
		return
	}

	if (uncountedRowCount(items.value) > 0) {
		showUncountedModal.value = true
		return
	}

	await persist('counted_only')
}

const confirmSave = async (mode: ReconciliationSaveMode) => {
	showUncountedModal.value = false
	await persist(mode)
}

const submit = async () => {
	if (!reconciliation.value.name) return
	const res = await store.submit('Stock Reconciliation', reconciliation.value.name)
	if (res?.data) {
		store.$patch(state => {
			;(state.cache.mappers['stock-reconciliation'] as StockReconciliation) = {
				name: '',
				purpose: 'Stock Reconciliation',
				items: [],
				set_warehouse: '',
			}
		})
		items.value = []
		componentKey.value++
	}
}

const cancel = async () => {
	store.$patch(state => {
		;(state.cache.mappers['stock-reconciliation'] as StockReconciliation) = {
			name: '',
			purpose: 'Stock Reconciliation',
			items: [],
			set_warehouse: '',
		}
	})
	items.value = []
	componentKey.value++
}

const controlButtons = computed((): ControlButton[] => {
	if (!items.value.length || !reconciliation.value.set_warehouse) return []
	return [
		{
			label: 'SAVE',
			disabled: items.value.length === 0,
			color: { background: '#4791FF', text: 'var(--sc-btn-color)' },
			action: trySave,
		},
		{
			label: 'SUBMIT',
			disabled: !reconciliation.value.name,
			hidden: !reconciliation.value.name,
			color: { background: 'var(--sc-success)', text: 'var(--sc-btn-color)' },
			action: submit,
		},
		{
			label: 'CANCEL',
			color: { background: 'white', text: 'black' },
			action: cancel,
		},
	]
})

watch(
	() => reconciliation.value.set_warehouse,
	warehouse => {
		resetItems()
		loadItemsFromWarehouse(warehouse)
	}
)

onMounted(async () => {
	store.setReconciliationItemScan(handleReconciliationScan)
	store.$patch(state => ((state.cache.mappers['stock-reconciliation'] as StockReconciliation) = reconciliation.value))
	warehouseList.value = store.warehouseList.filter(w => !w.is_group).map(w => w.name)
})

onUnmounted(() => {
	store.setReconciliationItemScan(null)
})
</script>
<style>
.reconciliation {
	margin-bottom: 1.5em;
}

.reconciliation-list {
	margin-left: var(--sc-list-margin);
	margin-right: var(--sc-list-margin);
	padding: 0 0 2.5em;
	list-style-type: none;
}

.reconciliation .clear-button {
	margin-bottom: 2px;
	padding: 0.9rem 1rem !important;
}

.reconciliation .dropdown-container {
	display: flex;
	align-items: flex-end !important;
	justify-content: center;
	position: relative;
	margin-top: 1rem;
	gap: 8px;
}

.reconciliation .autocomplete input,
.autocomplete-results {
	font-size: 150%;
}

.autocomplete-results {
	padding-inline: 3px !important;
}

.reconciliation .input-wrapper label {
	margin: calc(-2.5rem - calc(2.15rem / 2)) 0 0 1ch !important;
}

.beam_item-count {
	white-space: nowrap;
}

.reconciliation-modal-backdrop {
	position: fixed;
	inset: 0;
	background-color: rgba(0, 0, 0, 0.5);
	display: flex;
	align-items: center;
	justify-content: center;
	padding: 1rem;
	z-index: 1000;
}

.reconciliation-modal {
	background: white;
	padding: 1.25rem;
	border-radius: 4px;
	max-width: 24rem;
	width: 100%;
}

.reconciliation-modal-actions {
	display: flex;
	flex-direction: column;
	gap: 0.5rem;
	margin-top: 1rem;
}
</style>
