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
					<ADropdown
						label="Item to Repack"
						:items="itemList"
						v-model="currentItem.item_code"
						:isAsync="true"
						:filterFunction="loadItems"
					/>
					<BeamBtn class="clear-button" @click="clearCurrentItem"> X </BeamBtn>
				</div>
				<div class="dd-container wrapper">
					<BeamBtn class="clear-button" @click="substractCurrentItem"> - </BeamBtn>
					<!-- <div class="wrapper">
						<input label="Qty" type="number" v-model="currentItem.qty" />
					</div> -->
					<ANumericInput label="Quantity" v-model="currentItem.qty" />
					<BeamBtn class="clear-button" @click="addCurrentItem"> + </BeamBtn>
				</div>
				<div class="dd-container">
					<ADropdown label="BOM (Optional)" :items="bomList" v-model="currentItem.bom" />
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

	<ListView :items="items" :key="componentKey" @update="update" />
	<div class="begin" v-if="items.length == 0">
		<span>Scan Items, Select Warehouses, and Set Qty to Begin</span>
	</div>

	<ControlButtons :buttons="controlButtons" />
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useBeamStore } from '@/stores/beam'
import ControlButtons from '@/components/ControlButtons.vue'
import { ListViewItem } from '@stonecrop/beam'
import type { ControlButton, StockEntry } from '@/types'

const store = useBeamStore()
const currentItem = ref<ListViewItem>({ item_code: '', qty: 0, bom: '' })
const items = ref<ListViewItem[]>([])
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

const loadWarehouses = async () => {
	const warehouses = await store.getAll<{ name: string }[]>('Warehouse', {
		filters: JSON.stringify([['is_group', '!=', '1']]),
	})
	warehouseList.value = warehouses.map(warehouse => warehouse.name)
}

const clearField = (field: 'from_warehouse' | 'to_warehouse') => stockEntry.value[field] = ''

const clearCurrentItem = () => currentItem.value = { item_code: '', qty: 0, bom: '' }

const addCurrentItem = () => currentItem.value.qty++

const substractCurrentItem = () => currentItem.value.qty--

const update = () => {
	// TODO
}

const create = async () => {
	const body: StockEntry = {
		stock_entry_type: 'Repack',
		items: stockEntry.value.items || [],
		from_warehouse: stockEntry.value.from_warehouse,
		to_warehouse: stockEntry.value.to_warehouse,
		name: stockEntry.value.name,
	}
	let res = await store.insert<StockEntry>('Stock Entry', body)
	if (res?.data?.name) {
		stockEntry.value.name = res.data.name
	}
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

const controlButtons = computed((): ControlButton[] => {
	if (!stockEntry.value.items.length || !stockEntry.value.from_warehouse || !stockEntry.value.to_warehouse) return []
	return [
		{ label: 'SAVE', color: { background: '#4791FF', text: 'var(--sc-btn-color)' }, action: create },
		{ label: 'REPACK', disabled: !stockEntry.value.name, color: { background: 'var(--sc-success)', text: 'var(--sc-btn-color)' }, action: repack },
	]
})

watch(
	() => store.cache.mappers['repack']?.items,
	(newItems: ListViewItem[]) => {
		if (!newItems) return

		const item = newItems[0]
		if (!item) return
		itemList.value = [item.item_code]
		const qty = item.item_code === currentItem.value.item_code ? currentItem.value.qty + 1 : 1
		if (!currentItem.value.item_code) currentItem.value = { ...item, qty }
		else currentItem.value = { ...item, qty }

		store.$patch(state => state.cache.mappers.repack.items = [])
		//componentKey.value++
	},
	{ immediate: true, deep: true }
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