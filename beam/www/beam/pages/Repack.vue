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
					<ADropdown
						label="Item to Repack"
						:items="itemList"
						v-model="currentItem.item_code"
						:isAsync="true"
						:filterFunction="loadItems" />
					<BeamBtn class="clear-button" @click="clearCurrentItem('item_code')"> X </BeamBtn>
				</div>
				<div class="dd-container">
					<BeamBtn class="clear-button" @click="substractCurrentItem"> - </BeamBtn>
					<ANumericInput label="Quantity" v-model="currentItem.qty" />
					<BeamBtn class="clear-button" @click="addCurrentItem"> + </BeamBtn>
				</div>
				<fieldset class="dd-container bom-field" :disabled="bomDisabled">
					<ADropdown label="BOM (Optional)" :items="bomList" v-model="currentItem.bom" />
					<BeamBtn class="clear-button" @click="clearCurrentItem('bom')"> X </BeamBtn>
				</fieldset>
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
import { appendUomText, itemListLine } from '@/utils/itemListLine'
import { useBeamToast } from '@/utils/toast.js'

const toast = useBeamToast()
const store = useBeamStore()
const currentItem = ref({ item_code: '', qty: 0, bom: '', stock_uom: '', uom: '' })
const items = ref([])
const componentKey = ref(0)
const defaultRepackEntry = (): StockEntry => ({
	doctype: 'Stock Entry',
	name: '',
	stock_entry_type: 'Repack',
	purpose: 'Repack',
	items: [],
	from_warehouse: '',
	to_warehouse: '',
})

const stockEntry = computed(() => (store.cache.mappers.repack as StockEntry | undefined) || defaultRepackEntry())

const itemList = ref<string[]>([])
const bomList = ref<string[]>([])
const warehouseList = ref<string[]>([])

onMounted(async () => {
	store.$patch(state => (state.cache.mappers.repack = stockEntry.value))
	warehouseList.value = store.warehouseList.filter(w => !w.is_group).map(w => w.name)
})

const itemUoms = new Map<string, string>()
let latestItemQuery = 0

const loadItems = async () => {
	// ADropdown passes its pre-keystroke value to filterFunction; the v-model already holds the typed text.
	const search = currentItem.value.item_code
	const query = ++latestItemQuery
	if (!search) {
		itemList.value = []
		return []
	}
	const items = await store.getAll<{ name: string; stock_uom: string }[]>('Item', {
		filters: JSON.stringify([['item_code', 'like', `${search}%`]]),
		fields: JSON.stringify(['name', 'stock_uom']),
	})
	if (query !== latestItemQuery) return itemList.value
	for (const item of items) itemUoms.set(item.name, item.stock_uom)
	itemList.value = items.map(item => item.name)
	return itemList.value
}

const itemChosenForBom = computed(
	() =>
		itemList.value.includes(currentItem.value.item_code) ||
		(Boolean(currentItem.value.item_code.trim()) && itemUoms.has(currentItem.value.item_code))
)

const bomDisabled = computed(() => !itemChosenForBom.value)

watch(bomDisabled, disabled => {
	if (disabled) currentItem.value.bom = ''
})

watch(
	() => currentItem.value.item_code,
	async itemCode => {
		if (itemCode && !itemUoms.has(itemCode)) {
			const rows = await store.getAll<{ name: string; stock_uom: string }[]>('Item', {
				filters: JSON.stringify([['name', '=', itemCode]]),
				fields: JSON.stringify(['name', 'stock_uom']),
				limit_page_length: 1,
			})
			if (rows[0]) itemUoms.set(rows[0].name, rows[0].stock_uom)
		}
		const stockUom = itemUoms.get(itemCode)
		if (stockUom) currentItem.value.stock_uom = stockUom
		await loadBOMs(itemCode)
	}
)

const loadBOMs = async (itemCode: string) => {
	if (!itemCode.trim()) {
		bomList.value = []
		currentItem.value.bom = ''
		return
	}
	const boms = await store.getAll<{ name: string }[]>('BOM', {
		filters: JSON.stringify([
			['item', '=', itemCode],
			['is_active', '=', 1],
			['docstatus', '=', 1],
		]),
		fields: JSON.stringify(['name']),
	})
	bomList.value = boms.map(bom => bom.name)
	if (currentItem.value.bom && !bomList.value.includes(currentItem.value.bom)) {
		currentItem.value.bom = ''
	}
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
			state.cache.mappers.repack = defaultRepackEntry()
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
	const warehouse = stockEntry.value.from_warehouse || stockEntry.value.to_warehouse
	const line = itemListLine({
		item_code: currentItem.value.item_code,
		warehouse,
		stock_uom: currentItem.value.stock_uom,
		uom: currentItem.value.uom,
	})
	items.value.push({
		label: line.label || currentItem.value.item_code,
		count: { count: currentItem.value.qty },
		description: appendUomText(
			stockEntry.value.from_warehouse
				? `From ${stockEntry.value.from_warehouse}`
				: `To ${stockEntry.value.to_warehouse}`,
			currentItem.value
		),
		item_code: currentItem.value.item_code,
		qty: currentItem.value.qty,
		s_warehouse: stockEntry.value.from_warehouse,
		t_warehouse: stockEntry.value.to_warehouse,
		stock_uom: currentItem.value.stock_uom,
		uom: currentItem.value.uom,
	})

	currentItem.value = { item_code: '', qty: 0, bom: '', stock_uom: '', uom: '' }
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
			action: clearItem,
			hidden: items.value.length === 0,
		},
		{
			label: 'ADD',
			action: addItem,
		},
	]

	if (items.value.length === 0) return buttons
	return [
		{
			label: 'REPACK',
			disabled: !stockEntry.value.name,
			hidden: !stockEntry.value.name,
			action: repack,
		},
		{
			label: 'SAVE',
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
			mergedMap.set(item.item_code, { ...item })
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

		currentItem.value = {
			item_code: newItem.item_code || '',
			qty,
			bom: '',
			stock_uom: newItem.stock_uom || '',
			uom: newItem.uom || '',
		}
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
		items.value = listBom.map(bomItem => {
			const line = itemListLine({
				item_code: bomItem.item_code,
				item_name: bomItem.item_name,
				warehouse: bomItem.default_warehouse,
				stock_uom: bomItem.stock_uom,
			})
			return {
				label: line.label,
				count: { count: bomItem.qty },
				description: appendUomText(`From ${bomItem.default_warehouse}`, bomItem),
				item_code: bomItem.item_code,
				qty: bomItem.qty,
				s_warehouse: bomItem.default_warehouse,
				stock_uom: bomItem.stock_uom,
			}
		})
	}
)
</script>
<style>
.repack {
	display: flex;
	justify-content: center;
	align-items: center;
	min-height: 200px;
	padding: 0 var(--sc-list-margin);
	box-sizing: border-box;
}

.repack .begin {
	width: 100%;
	text-align: center;
	font-size: 1rem;
	color: var(--sc-primary-text-color);
	padding: 1rem var(--sc-list-margin);
	box-sizing: border-box;
}

.repack .autocomplete {
	flex: 1 1 auto;
	min-width: 0;
	width: 100%;
}

.max-h-300 {
	max-height: 300px;
	overflow: scroll;
	padding-bottom: 0px !important;
}

.repack .container {
	display: flex;
	flex-direction: column;
	width: min(80vh, 100%);
	max-width: 100%;
	padding: 0;
	box-sizing: border-box;
}

.repack .dd-container {
	display: flex;
	align-items: flex-end;
	width: 100%;
	margin-top: 1rem;
	gap: 0.5rem;
	justify-content: space-between;
}

.repack .dd-container .aform_form-element {
	margin: 0;
}

.repack fieldset.bom-field {
	border: 0;
	padding: 0;
	margin-left: 0;
	margin-right: 0;
	min-width: 0;
}

.repack fieldset.bom-field:disabled {
	opacity: 0.55;
}

.repack fieldset.bom-field:disabled input,
.repack fieldset.bom-field:disabled button {
	cursor: not-allowed;
}

.repack .clear-button {
	align-self: stretch;
	margin: 0;
	padding: 0 0.75rem;
	min-width: 2.75rem;
}
</style>
