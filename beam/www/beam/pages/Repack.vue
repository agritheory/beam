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
				<div class="dd-container">
					<ADropdown label="Item to Repack" :items="itemList" v-model="currentItem.item_code" :isAsync="true"
						:filterFunction="loadItems" />
					<BeamBtn class="clear-button" @click="clearCurrentItem('item_code')"> X </BeamBtn>
				</div>
				<div class="dd-container">
					<BeamBtn class="clear-button" @click="substractCurrentItem"> - </BeamBtn>
					<ANumericInput label="Quantity" v-model="currentItem.qty" />
					<BeamBtn class="clear-button" @click="addCurrentItem"> + </BeamBtn>
				</div>
				<div class="dd-container">
					<ADropdown label="BOM (Optional)" :items="bomList" v-model="currentItem.bom" />
					<BeamBtn class="clear-button" @click="clearCurrentItem('bom')"> X </BeamBtn>
				</div>
			</template>
			<div class="dd-container">
				<ADropdown label="Source Warehouse" :items="warehouseList" v-model="stockEntry.from_warehouse" />
				<BeamBtn class="clear-button" @click="clearField('from_warehouse')"> X </BeamBtn>
			</div>
			<div class="dd-container">
				<ADropdown label="Target Warehouse" :items="warehouseList" v-model="stockEntry.to_warehouse" />
				<BeamBtn class="clear-button" @click="clearField('to_warehouse')"> X </BeamBtn>
			</div>
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
import { useBeamStore } from '@/stores/beam'
import type { ControlButton, DocActionResponse, StockEntry } from '@/types'
import { useBeamToast } from '@/utils/toast.js'

const toast = useBeamToast()
const store = useBeamStore()
const currentItem = ref({ item_code: '', qty: 0, bom: '' })
const items = ref([])
const componentKey = ref(0)
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

const clearField = (field: 'from_warehouse' | 'to_warehouse') =>
	store.$patch(state => (state.cache.mappers.repack[field] = ''))

const addCurrentItem = () => currentItem.value.qty++
const substractCurrentItem = () => (currentItem.value.qty > 0 ? currentItem.value.qty-- : 0)
const clearCurrentItem = (field: 'item_code' | 'bom') => (currentItem.value[field] = '')

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
	const mergedMap = new Map<string, ListViewItem>();

	items.forEach(item => {
		const existing = mergedMap.get(item.item_code);
		if (existing) {
			mergedMap.set(
				item.item_code,
				{
					item_code: item.item_code,
					qty: item.transfer_qty || item.qty || 0,
					from_warehouse: item.s_warehouse || ''
				}
			);
		} else {
			mergedMap.set(item.item_code, { ...item });
		}
	});

	return Array.from(mergedMap.values());
}

watch(
	() => store.cache.mappers.repack?.items,
	(newItems: ListViewItem[]) => {
		// Update items list on Scan
		if (!newItems) return
		if (currentItem.value.bom) return
		const flattened = flattenItems(newItems);
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

.repack .autocomplete input,
.autocomplete-results {
	font-size: 150%;
}

.repack .input-wrapper label {
	margin: calc(-2.5rem - calc(2.15rem / 2)) 0 0 1ch !important;
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
}

.dd-container {
	display: flex;
	width: 100%;
	margin-top: 1rem;
	gap: 10px;
	justify-content: space-between;
}

.dd-container .aform_form-element input {
	border-color: red;
	font-size: 150% !important;
	outline: 1px solid transparent !important;
	border: 1px solid var(--sc-input-border-color) !important;
	border-radius: 0.25rem !important;
	width: 90% !important;
}

.dd-container .aform_form-element {
	margin-bottom: 0 !important;
	margin-top: 10px !important;
}

.clear-button {
	margin-top: 10px;
}
</style>
