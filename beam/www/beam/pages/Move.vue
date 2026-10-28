<template>
	<Navbar>
		<template #title>
			<h1>Move</h1>
		</template>
		<template #navbaraction>
			<RouterLink :to="{ name: 'home' }">Home</RouterLink>
		</template>
	</Navbar>
	<div class="move">
		<FieldRow>
			<ADropdown label="Source Warehouse" :options="warehouseList" v-model="stockEntry.from_warehouse" />
			<template #suffix>
				<BeamBtn @click="clearField('from_warehouse')"> X </BeamBtn>
			</template>
		</FieldRow>
		<FieldRow>
			<ADropdown label="Target Warehouse" :options="warehouseList" v-model="stockEntry.to_warehouse" />
			<template #suffix>
				<BeamBtn @click="clearField('to_warehouse')"> X </BeamBtn>
			</template>
		</FieldRow>
	</div>

	<!-- body section -->
	<ListView :items="items" :key="componentKey" @update="update" />
	<div class="begin" v-if="items.length == 0">
		<span>Scan Items and Scan or Select Warehouses to Begin</span>
	</div>
	<!-- footer section -->
	<ControlButtons :buttons="controlButtons" />
</template>

<script setup lang="ts">
import type { ListViewItem } from '@/types/stonecrop.js'
import { ref, onMounted, computed, watch } from 'vue'

import ControlButtons from '@/components/ControlButtons.vue'
import { useLineInspections } from '@/composables/useLineInspections'
import FieldRow from '@/components/FieldRow.vue'
import { useBeamStore } from '@/stores/beam'
import type { ControlButton, DocActionResponse, StockEntry, StockEntryItem } from '@/types'
import { itemListLine } from '@/utils/itemListLine'
import { applyInspectionLines } from '@/utils/inspectionList'
const store = useBeamStore()
const items = ref<(ListViewItem & Partial<StockEntryItem>)[]>([])
const stockEntry = computed(
	(): StockEntry =>
		(store.cache.mappers['move'] as StockEntry) || {
			name: '',
			stock_entry_type: 'Material Transfer',
			items: [],
			from_warehouse: '',
			to_warehouse: '',
		}
)
const componentKey = ref(0)

const savedEntryName = computed(() => stockEntry.value?.name || undefined)
const { byRow } = useLineInspections(
	computed(() => 'Stock Entry'),
	savedEntryName
)

const warehouseList = ref<string[]>([])

onMounted(async () => {
	store.form as Partial<StockEntry>
	store.$patch(state => (state.cache.mappers['move'] = stockEntry.value))
	warehouseList.value = store.warehouseList.filter(w => !w.is_group).map(w => w.name)
})

const clearField = (field: 'from_warehouse' | 'to_warehouse') => {
	store.$patch(state => {
		const mapper = state.cache.mappers['move']
		if (mapper) mapper[field] = ''
	})
}

const update = () => {
	// TODO
}

// store.$subscribe((mutation, state) => {
// 	const parentfield = state.form.doctype === 'Work Order' ? 'required_items' : 'items'
// 	if (parentfield && state.form[parentfield]) {
// 		items.value = []
// 		state.form[parentfield].forEach(item => {
// 			item.wip_warehouse = state.form.wip_warehouse
// 			items.value.push({
// 				label: item.item_name,
// 				description: `${item.source_warehouse} > ${item.wip_warehouse}`,
// 				count: {
// 					count: item.transferred_qty,
// 					of: item.required_qty,
// 				},
// 			})
// 		})
// 		componentKey.value++
// 	}
// })

const create = async () => {
	const body: StockEntry = {
		stock_entry_type: 'Material Transfer',
		items: stockEntry.value.items.map(i => ({
			...i,
			s_warehouse: stockEntry.value.from_warehouse,
			t_warehouse: stockEntry.value.to_warehouse,
		})),
		name: stockEntry.value.name,
	}
	let res: DocActionResponse<StockEntry>

	if (body.name) {
		res = await store.update<StockEntry>('Stock Entry', body.name, body)
	} else {
		res = await store.insert<StockEntry>('Stock Entry', body)
	}
	const { data, response } = res
	if (data.name) {
		stockEntry.value.name = data.name
	}
	return { data, response }
}

const move = async () => {
	const res = await store.submit<StockEntry>('Stock Entry', stockEntry.value.name)
	if (res?.data)
		store.$patch(state => {
			state.cache.mappers['move'] = {
				name: '',
				stock_entry_type: 'Material Transfer',
				items: [],
				from_warehouse: '',
				to_warehouse: '',
			}
		})
}

const controlButtons = computed((): ControlButton[] => {
	if (!stockEntry.value.items.length || !stockEntry.value.from_warehouse || !stockEntry.value.to_warehouse) return []
	return [
		{
			label: 'SAVE',
			disabled: items.value.length === 0,
			action: create,
		},
		{
			label: 'MOVE',
			disabled: !stockEntry.value.name,
			hidden: !stockEntry.value.name,
			color: { background: 'var(--sc-success)', text: 'var(--sc-btn-color)' },
			action: move,
		},
	]
})

watch(
	[() => store.cache.mappers['move']?.items, byRow],
	() => {
		const newItems = store.cache.mappers['move']?.items
		const mapped = (newItems || []).map(s => {
			const line = itemListLine({
				...s,
				warehouse: s.s_warehouse || s.t_warehouse,
			})
			return {
				...s,
				label: line.label || s.item_code,
				description: line.description,
				count: { count: s.qty ?? 0, of: 0 },
			}
		})
		items.value = applyInspectionLines(mapped, byRow.value)
		componentKey.value++
	},
	{ immediate: true, deep: true }
)
</script>

<style>
.move {
	display: flex;
	flex-direction: column;
	gap: 1rem;
	margin-bottom: 1.5em;
	padding: 20px;
}

.autocomplete-results {
	font-size: 150%;
	padding-inline: 3px !important;
}

.begin {
	width: 100%;
	text-align: center;
	font-size: 150%;
	text-wrap: balance;
}
</style>
