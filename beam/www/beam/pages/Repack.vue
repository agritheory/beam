<template>
	<Navbar>
		<template #title>
			<h1>Repack</h1>
		</template>
		<template #navbaraction>
			<RouterLink :to="{ name: 'home' }">Home</RouterLink>
		</template>
	</Navbar>

	<div class="move">
		<div class="container">
			<template v-if="itemList">
				<div class="dd-container">
					<ADropdown label="Item to Repack" :items="itemList" v-model="currentItem.item_code" :isAsync="true"
						:filterFunction="loadItems" />
					<BeamBtn class="clear-button" @click="clearCurrentItem('item_code')"> X </BeamBtn>
				</div>
				<div class="dd-container wrapper">
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

	<ListView v-if="items.length > 0" :items="items" :key="componentKey" />
	<div class="begin" v-else>
		<span>Scan Items, Select Warehouses, and Set Qty to Begin</span>
	</div>

	<ControlButtons :buttons="controlButtons" />
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useBeamStore } from '@/stores/beam'
import { useHttpStore } from '@/stores/http.js'
import { useBeamToast } from '@/utils/toast.js'
import { ListViewItem } from '@stonecrop/beam'
import ControlButtons from '@/components/ControlButtons.vue'
import type { ControlButton, DocActionResponse, StockEntry, BomItem } from '@/types'

const httpStore = useHttpStore()
const toast = useBeamToast()
const store = useBeamStore()
const currentItem = ref({ item_code: '', qty: 0, bom: '' })
const items = ref([])
const componentKey = ref(0)
const stockEntry = computed(
	(): StockEntry =>
		(store.cache.mappers['repack'] as StockEntry) || {
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
	store.$patch(state => state.cache.mappers['repack'] = stockEntry.value)
	await loadBOMs()
	await loadWarehouses()
})

const loadItems = async (search: string) => {
	if (!search) return []
	const itemsData = await store.getAll<{ name: string }[]>('Item', {
		filters: JSON.stringify([['item_code', 'like', `${search}%`]]),
	})
	const itemsMapped = itemsData.map(item => item.name)
	itemList.value = itemsMapped
	return itemsMapped.filter(item => item.toLocaleLowerCase().startsWith(search.toLocaleLowerCase()))
}

const loadBOMs = async () => {
	const boms = await store.getAll<{ name: string }[]>('BOM')
	bomList.value = boms.map(bom => bom.name)
}

const getStockEntryItems = async (bomName: string, company = "Ambrosia Pie Company", qty = 1, purpose = "Manufacture") => {
	try {
		const response = await httpStore.get("/api/method/erpnext.manufacturing.doctype.bom.bom.get_bom_items", {
			bom: bomName,
			company,
			fetch_exploded: 1,
			qty,
			purpose,
		})
		const { message }: { message: BomItem[] } = await response.json()

		if (!message) {
			console.error("La respuesta no contiene 'message'", response)
			return []
		}

		return message
	} catch (error) {
		console.error("Error en getStockEntryItems:", error)
		return []
	}
}

const loadWarehouses = async () => {
	const warehouses = await store.getAll<{ name: string }[]>('Warehouse', {
		filters: JSON.stringify([['is_group', '!=', '1']]),
	})
	warehouseList.value = warehouses.map(warehouse => warehouse.name)
}

const clearField = (field: 'from_warehouse' | 'to_warehouse') => stockEntry.value[field] = ''

const clearCurrentItem = (field: 'item_code' | 'bom') => currentItem.value[field] = ''

const substractCurrentItem = () => currentItem.value.qty--

const addCurrentItem = () => currentItem.value.qty++

const create = async () => {
	const body: StockEntry = {
		stock_entry_type: 'Repack',
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
	if (data?.name) stockEntry.value.name = data.name

	return { data, response }
}

const repack = async () => {
	const res = await store.submit<StockEntry>('Stock Entry', stockEntry.value.name || '')
	if (res?.data) {
		store.$patch(state => {
			state.cache.mappers['repack'] = {
				name: '',
				stock_entry_type: 'Repack',
				items: [],
				from_warehouse: '',
				to_warehouse: '',
			}
		})
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
	items.value.push(
		{
			label: currentItem.value.item_code,
			count: { count: currentItem.value.qty },
			description: `From ${stockEntry.value.from_warehouse} to ${stockEntry.value.to_warehouse}`,
		}
	)
	currentItem.value = { item_code: '', qty: 0, bom: '' }
}

const clearItem = () => {
	currentItem.value.bom = ""
	items.value = []
	store.$patch(state => state.cache.mappers.repack.items = [])
}

const controlButtons = computed((): ControlButton[] => {
	const buttons = [
		{ label: 'CLEAN', color: { background: '#4791FF', text: 'var(--sc-btn-color)' }, action: clearItem },
		{ label: 'ADD', color: { background: '#4791FF', text: 'var(--sc-btn-color)' }, action: addItem },
	]
	if (!(stockEntry.value.items.length || stockEntry.value.bom) || !stockEntry.value.from_warehouse || !stockEntry.value.to_warehouse) return buttons
	return [
		{
			label: 'REPACK',
			disabled: !stockEntry.value.name,
			hidden: !stockEntry.value.name,
			color: {
				background: '#4791FF',
				text: 'var(--sc-btn-color)'
			},
			action: repack
		},
		{
			label: 'SAVE',
			color: {
				background: '#4791FF',
				text: 'var(--sc-btn-color)'
			},
			action: create
		},
		...buttons,
	]
})

watch(
	() => store.cache.mappers['repack']?.items,
	(newItems: ListViewItem[]) => {
		if (currentItem.value.bom) return
		if (!newItems) return

		const item = newItems[0]
		if (!item) return
		itemList.value = [item.item_code]
		const qty = item.item_code === currentItem.value.item_code ? currentItem.value.qty + 1 : 1

		if (!currentItem.value.item_code) currentItem.value = { ...item, qty }
		else currentItem.value = { ...item, qty }
	},
	{ immediate: true, deep: true }
)

watch(
	() => currentItem.value.bom,
	async (bom) => {
		const listBom = await getStockEntryItems(bom);
		items.value = listBom.map(bomItem => ({
			label: bomItem.description,
			count: { count: bomItem.qty },
			description: `${bomItem.default_warehouse}`,
		}))
		stockEntry.value.items = listBom.map(bomItem => ({
			item_code: bomItem.description,
			qty: bomItem.qty,
			s_warehouse: bomItem.default_warehouse,
		}))
	}
)
</script>
<style scoped>
.move {
	display: flex;
	justify-content: center;
	align-items: center;
	min-height: 200px;
	padding: 20px;
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

/* .wrapper .aform_form-element input {
	font-size: 150% !important;
	outline: 1px solid transparent !important;
	border: 1px solid var(--sc-input-border-color) !important;
	border-radius: .25rem !important;
} */

.clear-button {
	margin-top: 10px;
}
</style>