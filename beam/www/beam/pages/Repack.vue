<template>
	<Navbar>
		<template #title>
			<h1>Repack</h1>
		</template>
		<template #navbaraction>
			<RouterLink :to="{ name: 'home' }">Home</RouterLink>
		</template>
	</Navbar>

	<div class="repack">
		<div class="container">
			<template v-if="itemList">
				<FieldRow>
					<ADropdown
						:key="itemCodeKey"
						label="Item to Repack"
						:options="itemList"
						v-model="itemCodeModel"
						:isAsync="true"
						:filterFunction="loadItems" />
					<template #suffix>
						<BeamBtn @click="clearCurrentItem('item_code')"> X </BeamBtn>
					</template>
				</FieldRow>
				<FieldRow>
					<template #prefix>
						<BeamBtn @click="substractCurrentItem"> - </BeamBtn>
					</template>
					<ANumericInput label="Quantity" v-model="qtyModel" />
					<template #suffix>
						<BeamBtn @click="addCurrentItem"> + </BeamBtn>
					</template>
				</FieldRow>
				<FieldRow>
					<ADropdown :key="bomKey" label="BOM (Optional)" :options="bomList" v-model="bomModel" />
					<template #suffix>
						<BeamBtn @click="clearCurrentItem('bom')"> X </BeamBtn>
					</template>
				</FieldRow>
			</template>
			<FieldRow>
				<ADropdown
					:key="fromWarehouseKey"
					label="Source Warehouse"
					:options="warehouseList"
					v-model="stockEntry.from_warehouse" />
				<template #suffix>
					<BeamBtn @click="clearField('from_warehouse')"> X </BeamBtn>
				</template>
			</FieldRow>
			<FieldRow>
				<ADropdown
					:key="toWarehouseKey"
					label="Target Warehouse"
					:options="warehouseList"
					v-model="stockEntry.to_warehouse" />
				<template #suffix>
					<BeamBtn @click="clearField('to_warehouse')"> X </BeamBtn>
				</template>
			</FieldRow>
		</div>
	</div>

	<ListView v-if="items.length > 0" :items="items" :key="componentKey" class="max-h-300" />
	<div class="begin" v-else>
		<span>Scan Items, Select Warehouses, and Set Qty to Begin</span>
	</div>
	<ControlButtons :buttons="controlButtons" />
</template>

<script setup lang="ts">
import type { ListViewItem } from '@stonecrop/beam'
import { ref, computed, onMounted, watch } from 'vue'

import ControlButtons from '@/components/ControlButtons.vue'
import FieldRow from '@/components/FieldRow.vue'
import { useBeamStore } from '@/stores/beam'
import type { ControlButton, DocActionResponse, StockEntry } from '@/types'
import { useBeamToast } from '@/utils/toast.js'

const toast = useBeamToast()
const store = useBeamStore()
const currentItem = ref({ item_code: '', qty: 0, bom: '' })
const items = ref([])
const componentKey = ref(0)

const itemCodeModel = computed<string | undefined>({
	get: () => currentItem.value.item_code,
	set: value => {
		currentItem.value.item_code = value ?? ''
	},
})

const bomModel = computed<string | undefined>({
	get: () => currentItem.value.bom,
	set: value => {
		currentItem.value.bom = value ?? ''
	},
})

const qtyModel = computed<number | null | undefined>({
	get: () => currentItem.value.qty,
	set: value => {
		currentItem.value.qty = value ?? 0
	},
})
const stockEntry = computed(
	() =>
		store.cache.mappers.repack || {
			name: '',
			stock_entry_type: 'Repack',
			items: [],
			from_warehouse: '',
			to_warehouse: '',
		}
)

const itemList = ref<string[]>([])
const bomList = ref<string[]>([])
const warehouseList = ref<string[]>([])
const itemCodeKey = ref(0)
const bomKey = ref(0)
const fromWarehouseKey = ref(0)
const toWarehouseKey = ref(0)

onMounted(async () => {
	store.$patch(state => (state.cache.mappers.repack = stockEntry.value))
	await loadBOMs()
	warehouseList.value = store.warehouseList.filter(w => !w.is_group).map(w => w.name)
})

const loadItems = async (search: string) => {
	if (!search) return []
	const items = await store.getAll<{ name: string }[]>('Item', {
		filters: JSON.stringify([['item_code', 'like', `${search}%`]]),
	})
	itemList.value = items.map(item => item.name)
	return itemList.value.filter(item => item.toLocaleLowerCase().startsWith(search.toLocaleLowerCase()))
}

const loadBOMs = async () => {
	const boms = await store.getAll<{ name: string }[]>('BOM')
	bomList.value = boms.map(bom => bom.name)
}

const clearField = (field: 'from_warehouse' | 'to_warehouse') => {
	store.$patch(state => (state.cache.mappers.repack[field] = ''))
	if (field === 'from_warehouse') fromWarehouseKey.value++
	else toWarehouseKey.value++
}

const addCurrentItem = () => currentItem.value.qty++
const substractCurrentItem = () => (currentItem.value.qty > 0 ? currentItem.value.qty-- : 0)
const clearCurrentItem = (field: 'item_code' | 'bom') => {
	currentItem.value[field] = ''
	if (field === 'item_code') itemCodeKey.value++
	else bomKey.value++
}

const create = async () => {
	const body: StockEntry = {
		stock_entry_type: 'Repack',
		items: items.value,
		name: stockEntry.value.name,
	}
	let res: DocActionResponse<StockEntry>

	if (body.name) {
		res = await store.update<StockEntry>('Stock Entry', body.name, body)
	} else {
		res = await store.insert<StockEntry>('Stock Entry', body)
	}
	const { data, response } = res
	if (data?.name) store.$patch(state => (state.cache.mappers.repack.name = data.name))

	return { data, response }
}

const repack = async () => {
	const res = await store.submit<StockEntry>('Stock Entry', stockEntry.value.name || '')
	if (res?.data) {
		store.$patch(state => {
			state.cache.mappers.repack = {
				name: '',
				stock_entry_type: 'Repack',
				items: [],
				from_warehouse: '',
				to_warehouse: '',
			}
		})
		items.value = []
	}
}

const addItem = () => {
	if (!currentItem.value.item_code || !currentItem.value.qty) {
		toast.error('Please select or scan an Item and set its quantity')
		return
	}
	if (!stockEntry.value.from_warehouse && !stockEntry.value.to_warehouse) {
		toast.error('Please select source or target warehouses')
		return
	}
	if (stockEntry.value.from_warehouse && stockEntry.value.to_warehouse) {
		toast.error('Please select only source or target warehouse')
		return
	}
	items.value.push({
		label: currentItem.value.item_code,
		count: { count: currentItem.value.qty },
		description: stockEntry.value.from_warehouse
			? `From ${stockEntry.value.from_warehouse}`
			: `To ${stockEntry.value.to_warehouse}`,
		item_code: currentItem.value.item_code,
		qty: currentItem.value.qty,
		s_warehouse: stockEntry.value.from_warehouse,
		t_warehouse: stockEntry.value.to_warehouse,
	})

	currentItem.value = { item_code: '', qty: 0, bom: '' }
	clearField('from_warehouse')
	clearField('to_warehouse')
}

const clearItem = () => {
	currentItem.value.bom = ''
	items.value = []
	store.$patch(state => (state.cache.mappers.repack.items = []))
}

const controlButtons = computed((): ControlButton[] => {
	const buttons = [
		{
			label: 'CLEAN',
			color: {
				background: '#4791FF',
				text: 'var(--sc-btn-color)',
			},
			action: clearItem,
			hidden: items.value.length === 0,
		},
		{
			label: 'ADD',
			color: {
				background: '#4791FF',
				text: 'var(--sc-btn-color)',
			},
			action: addItem,
		},
	]

	if (items.value.length === 0) return buttons
	return [
		{
			label: 'REPACK',
			disabled: !stockEntry.value.name,
			hidden: !stockEntry.value.name,
			color: {
				background: '#4791FF',
				text: 'var(--sc-btn-color)',
			},
			action: repack,
		},
		{
			label: 'SAVE',
			color: {
				background: '#4791FF',
				text: 'var(--sc-btn-color)',
			},
			action: create,
		},
		...buttons,
	]
})

function flattenItems(items: ListViewItem[]): ListViewItem[] {
	const mergedMap = new Map<string, ListViewItem>()

	items.forEach(item => {
		const existing = mergedMap.get(item.item_code)
		if (existing) {
			mergedMap.set(item.item_code, {
				item_code: item.item_code,
				qty: item.transfer_qty || item.qty || 0,
				from_warehouse: item.s_warehouse || '',
			})
		} else {
			mergedMap.set(item.item_code, { ...item, from_warehouse: item.s_warehouse || '' })
		}
	})

	return Array.from(mergedMap.values())
}

watch(
	() => store.cache.mappers.repack?.items,
	(newItems: ListViewItem[]) => {
		// Update items list on Scan
		if (!newItems) return
		if (currentItem.value.bom) return
		const flattened = flattenItems(newItems)
		const newItem = flattened[flattened.length - 1]
		if (!newItem) return
		const itemExists = items.value.some(i => i.label === newItem.item_code)
		// if (itemExists) {
		// 	toast.error(`${newItem.item_code} already added`)
		// 	return
		// }
		itemList.value = [newItem.item_code] // ADropdown needs the list to keep the selected item
		const qty = newItem.item_code === currentItem.value.item_code ? currentItem.value.qty + newItem.qty : newItem.qty

		currentItem.value = { ...newItem, qty }
		if (newItem.from_warehouse) stockEntry.value.from_warehouse = newItem.from_warehouse
		store.$patch(state => (state.cache.mappers.repack.items = []))
	},
	{ immediate: true, deep: true }
)

watch(
	() => currentItem.value.bom,
	async bom => {
		// Update items list on BOM selection
		if (!currentItem.value.bom) return
		const listBom = await store.getStockEntryItems(bom)
		items.value = listBom.map(bomItem => ({
			label: bomItem.description,
			count: { count: bomItem.qty },
			description: `From ${bomItem.default_warehouse}`,
			item_code: bomItem.description,
			qty: bomItem.qty,
			s_warehouse: bomItem.default_warehouse,
		}))
	}
)
</script>
<style>
.repack {
	display: flex;
	justify-content: center;
	align-items: center;
	min-height: 200px;
	padding: 20px;
}

.autocomplete-results {
	font-size: 150%;
}

.max-h-300 {
	max-height: 300px;
	overflow: scroll;
	padding-bottom: 0px !important;
}

.container {
	display: flex;
	flex-direction: column;
	width: 80vh;
	gap: 1rem;
}
</style>
