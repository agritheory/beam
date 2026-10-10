<template>
	<div class="work-order-page">
		<!-- navigation section -->
		<Navbar>
			<template #title>
				<h1>{{ workOrderId || 'Work Order' }}</h1>
				<span v-if="stockEntry?.dirty" class="dirty">Unsaved</span>
			</template>
			<template #navbaraction>
				<RouterLink :to="{ name: 'home' }">Home</RouterLink>
			</template>
		</Navbar>

		<!-- scan section -->
		<ScanOutput v-if="showScanSection" />

		<!-- body section -->
		<BeamMetadata class="box">
			<div style="padding: 1rem">
				<SplitColumn>
					<template #left>
						<p class="beam_metadata_heading">{{ workOrder.production_item }}</p>
						<p class="beam--normal">
							{{ transferProgress.transferred }} / {{ transferProgress.total }} ({{ transferProgress.percent }}%)
						</p>
						<p v-if="stageLabel" class="beam--normal stage-label">{{ stageLabel }}</p>
					</template>
					<template #right>
						<p class="beam--normal">{{ workOrder.planned_start_date }}</p>
						<p class="beam--normal">
							{{ operationProgress.completed }} / {{ operationProgress.total }} ({{ operationProgress.percent }}%)
						</p>
					</template>
				</SplitColumn>
			</div>
		</BeamMetadata>
		<div class="box predecessor-box" v-show="predecessorItems.length">
			<ListView :items="predecessorItems" :key="refreshKey" />
		</div>
		<p v-if="predecessorsBlock" class="predecessor-warning">Complete predecessor work orders before continuing.</p>
		<div class="box" v-show="items.length">
			<ListView :items="items" @update="updateItem" :key="refreshKey" />
			<div class="pick-list-link" v-if="pickListName">
				<RouterLink :to="{ name: 'pick_list', params: { id: pickListName } }">View Pick List</RouterLink>
			</div>
		</div>
		<div class="box" v-show="operations.length">
			<ListView :items="operations" :key="refreshKey" />
		</div>

		<!-- footer section -->
		<ControlButtons :buttons="controlButtons" />
	</div>
</template>

<script setup lang="ts">
import type { ListViewItem } from '@stonecrop/beam'
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute } from 'vue-router'

import ControlButtons from '@/components/ControlButtons.vue'
import ScanOutput from '@/components/ScanOutput.vue'
import { useBeamStore } from '@/stores/beam'
import type {
	ControlButton,
	DocActionResponse,
	StockEntry,
	StockEntryItem,
	WorkOrder,
	WorkOrderItem,
	WorkOrderOperation,
} from '@/types'
import { appendUomText, itemListLine } from '@/utils/itemListLine'
import { computeWorkOrderStage, type WorkOrderStage } from '@/utils/workOrderStage'

type OrderItem = WorkOrderItem & StockEntryItem & ListViewItem
type OrderOperation = WorkOrderOperation & ListViewItem

const route = useRoute()
const store = useBeamStore()
const workOrderId = route.params.id.toString()

const stockEntry = ref<StockEntry | undefined>(store.cache.mappers[workOrderId] as StockEntry)
const workOrder = ref(store.form as WorkOrder)
const refreshKey = ref(0)

store.$subscribe(mutation => {
	if (['patch function', 'patch object'].includes(mutation.type)) {
		refreshKey.value++
		workOrder.value = store.form as WorkOrder
		stockEntry.value = store.cache.mappers[workOrderId] as StockEntry
	}
})

onMounted(async () => {
	await store.getWorkOrderMobileContext(workOrderId)
})

const mobileContext = computed(() => store.workOrderContext[workOrderId])
const overproductionPercentage = computed(() => mobileContext.value?.overproduction_percentage || 0)
const predecessorsBlock = computed(() => Boolean(mobileContext.value?.predecessors_block))
const pickListName = computed(() => mobileContext.value?.pick_list || '')
const usesPickList = computed(() => Boolean(pickListName.value))

const stage = computed((): WorkOrderStage => computeWorkOrderStage(workOrder.value, overproductionPercentage.value))

const stageLabel = computed((): string => {
	switch (stage.value) {
		case 'ready_to_transfer':
			return 'Ready to transfer materials'
		case 'in_operations':
			return 'Operations in progress'
		case 'ready_to_manufacture':
			return 'Ready to manufacture'
		case 'stopped':
			return 'Stopped'
		case 'draft':
			return 'Draft'
		default:
			return workOrder.value.status || ''
	}
})

const showScanSection = computed(
	(): boolean => !usesPickList.value && (stage.value === 'ready_to_transfer' || stage.value === 'ready_to_manufacture')
)

const predecessorItems = computed((): ListViewItem[] => {
	return (mobileContext.value?.predecessors || []).map(row => ({
		barcode: row.work_order,
		label: `${row.work_order} · ${row.item_code}`,
		description: appendUomText(row.status || '', { stock_uom: row.stock_uom }),
		count: {
			count: row.produced_qty,
			of: row.required_qty,
		},
		linkComponent: 'ListAnchor',
		route: `#/work_order/${row.work_order}`,
	}))
})

const items = computed((): OrderItem[] => {
	if (usesPickList.value) {
		return (workOrder.value.required_items || []).map(item => {
			const line = itemListLine(item)
			return {
				...item,
				label: line.label,
				description: line.description,
				count: {
					count: item.transferred_qty,
					of: item.required_qty,
					editable: false,
				},
			}
		})
	}
	if (!stockEntry.value) return []
	return (workOrder.value.required_items || []).map(item => {
		const stockEntryItem = stockEntry.value?.items.find(i => i.item_code === item.item_code)
		const line = itemListLine(item)
		return {
			...stockEntryItem,
			...item,
			label: line.label,
			description: line.description,
			count: {
				count: stockEntryItem?.qty || item.transferred_qty,
				of: item.required_qty,
			},
		}
	})
})

const operations = computed((): OrderOperation[] => {
	return (workOrder.value.operations || []).map(operation => ({
		...operation,
		label: operation.operation,
		count: {
			count: operation.completed_qty,
			of: workOrder.value.qty,
		},
		linkComponent: 'ListAnchor',
		description: appendUomText(`${operation.workstation} - ${operation.time_in_mins}:00`, workOrder.value),
		route: `#/work_order/${workOrder.value.name}/operation/${operation.name}`,
	}))
})

const transferProgress = reactive({
	transferred: computed(() =>
		items.value.reduce<number>(
			(sum, item) => sum + (usesPickList.value ? item.transferred_qty || 0 : item.qty || item.transferred_qty || 0),
			0
		)
	),
	total: computed(() => items.value.reduce<number>((sum, item) => sum + (item.required_qty || 0), 0)),
	percent: computed(() =>
		transferProgress.total === 0 ? '0' : `${((transferProgress.transferred / transferProgress.total) * 100).toFixed(0)}`
	),
})

const operationProgress = reactive({
	completed: computed(() => operations.value.reduce((sum, operation) => sum + (operation.completed_qty || 0), 0) || 0),
	total: computed(() => (workOrder.value.qty || 0) * operations.value.length),
	percent: computed(() =>
		operationProgress.total === 0
			? '0'
			: `${((operationProgress.completed / operationProgress.total) * 100).toFixed(0)}`
	),
})

const persistStockEntry = async (): Promise<boolean> => {
	if (!stockEntry.value) return false

	const hasQuantities = stockEntry.value.items.some(item => (item.qty || 0) > 0)
	if (!stockEntry.value.dirty && stockEntry.value.name && !hasQuantities) {
		return true
	}
	if (!stockEntry.value.dirty && stockEntry.value.name && hasQuantities) {
		stockEntry.value.dirty = true
	}

	const document: StockEntry = { ...stockEntry.value }
	document.items = document.items.filter(item => item.qty > 0)

	let response: DocActionResponse<StockEntry>
	if (stockEntry.value.name) {
		response = await store.update('Stock Entry', document.name, document)
	} else {
		response = await store.insert('Stock Entry', document)
	}

	if (response.exception || !response.data) {
		return false
	}

	store.$patch(state => {
		stockEntry.value = response.data!
		stockEntry.value.dirty = false
		state.cache.mappers[workOrderId] = stockEntry.value
		state.form = workOrder.value
	})
	return true
}

const reloadAfterWorkOrderChange = async (): Promise<void> => {
	await store.refreshWorkOrderForm(workOrderId)
	workOrder.value = store.form as WorkOrder
	await store.setMappedDoc(route)
	stockEntry.value = store.cache.mappers[workOrderId] as StockEntry
	refreshKey.value++
}

const submitStageStockEntry = async (): Promise<void> => {
	const form = stockEntry.value as StockEntry
	if (!form?.items?.length) return

	const saved = await persistStockEntry()
	if (!saved || !stockEntry.value?.name) return

	await store.submit<StockEntry>('Stock Entry', stockEntry.value.name)
	await reloadAfterWorkOrderChange()
}

const controlButtons = computed((): ControlButton[] => {
	const form = stockEntry.value as StockEntry
	const buttons: ControlButton[] = []

	if (workOrder.value.docstatus === 1 && workOrder.value.status === 'Stopped') {
		buttons.push({
			label: 'RESUME',
			action: async () => {
				await store.setWorkOrderStatus(workOrderId, 'Resumed')
				await reloadAfterWorkOrderChange()
			},
		})
	} else {
		if (stage.value === 'ready_to_transfer' && !usesPickList.value) {
			buttons.push({
				label: 'TRANSFER',
				disabled: items.value.length === 0 || predecessorsBlock.value,
				color: { background: 'var(--sc-success)', text: 'var(--sc-btn-color)' },
				action: submitStageStockEntry,
			})
		} else if (stage.value === 'ready_to_manufacture') {
			buttons.push({
				label: 'MANUFACTURE',
				disabled: !form?.items?.length || predecessorsBlock.value,
				color: { background: 'var(--sc-success)', text: 'var(--sc-btn-color)' },
				action: submitStageStockEntry,
			})
		}

		if (
			workOrder.value.docstatus === 1 &&
			!['Stopped', 'Closed', 'Completed', 'Cancelled'].includes(workOrder.value.status || '')
		) {
			buttons.push({
				label: 'STOP',
				color: { background: 'var(--sc-beam-danger-fill)', text: 'var(--sc-btn-color)' },
				action: async () => {
					await store.setWorkOrderStatus(workOrderId, 'Stopped')
					await reloadAfterWorkOrderChange()
				},
			})
		}
	}

	// Always last: ControlButtons gives the last slot full width so hidden CANCEL keeps
	// the visible actions on one 50/50 row (same pattern as Delivery Note / old Work Order).
	buttons.push({
		label: 'CANCEL',
		disabled: !form?.name,
		hidden: !form?.name || form.docstatus !== 1,
		color: { background: 'var(--sc-beam-danger-fill)', text: 'var(--sc-btn-color)' },
		action: async () => {
			if (!form?.name) return
			await store.cancel<StockEntry>('Stock Entry', form.name)
			await reloadAfterWorkOrderChange()
		},
	})

	return buttons
})

const updateItem = (value: OrderItem) => {
	if (usesPickList.value || !stockEntry.value) return

	let itemModified = false
	for (const item of stockEntry.value.items) {
		if (item.item_code === value.item_code && item.qty !== value.count.count) {
			item.qty = value.count.count
			itemModified = true
			break
		}
	}

	if (itemModified) {
		store.$patch(state => {
			stockEntry.value!.dirty = true
			state.cache.mappers[workOrderId] = stockEntry.value
		})
	}
}
</script>

<style scoped>
.work-order-page {
	box-sizing: border-box;
	width: 100%;
	max-width: 100%;
	overflow-x: hidden;
}

.work-order-page :deep(.beam_list-item) {
	align-items: flex-start;
	gap: 0.75rem;
}

.work-order-page :deep(.beam_list-text) {
	flex: 1 1 auto;
	width: auto;
	min-width: 0;
	max-width: none;
	white-space: normal;
}

.work-order-page :deep(.beam_list-text label),
.work-order-page :deep(.beam_list-text p) {
	white-space: normal;
	overflow: visible;
	text-overflow: unset;
}

b {
	display: flex;
	justify-content: center;
	align-items: center;
}

.box {
	padding: 0rem;
	margin: 0.5rem;
	font-size: 100%;
	border: 1px solid var(--sc-row-border-color);
	border-radius: 0;
	outline: 2px solid transparent;
	flex: 1;
	min-width: 0;
	max-width: calc(100% - 1rem);
	box-sizing: border-box;
}

.dirty {
	color: var(--sc-beam-danger-fill);
	font-weight: 700;
}

.stage-label {
	font-weight: 600;
}

.predecessor-warning {
	margin: 0 0.75rem 0.5rem;
	color: var(--sc-beam-warning-text);
	font-size: 0.9rem;
}

.pick-list-link {
	padding: 1rem;
	text-align: center;
	border-top: 1px solid var(--sc-row-border-color);
}

.pick-list-link a {
	font-size: 1.1rem;
	font-weight: 600;
}
</style>
