<template>
	<Navbar>
		<template #title>
			<h1>Pick List</h1>
			<span v-if="pickList?.dirty" class="dirty">Unsaved</span>
		</template>
		<template #navbaraction>
			<RouterLink v-if="pickList?.work_order" :to="{ name: 'work_order', params: { id: pickList.work_order } }">
				Back
			</RouterLink>
			<RouterLink v-else :to="{ name: 'home' }">Home</RouterLink>
		</template>
	</Navbar>

	<ScanOutput />

	<div class="box" v-show="items.length">
		<ListView :items="items" :key="refreshKey" @update="updateItem" />
	</div>

	<ControlButtons :buttons="controlButtons" />
</template>

<script setup lang="ts">
import type { ListViewItem } from '@stonecrop/beam'
import { computed, ref } from 'vue'
import { onBeforeRouteLeave, useRoute } from 'vue-router'

import ControlButtons from '@/components/ControlButtons.vue'
import ScanOutput from '@/components/ScanOutput.vue'
import { useBeamStore } from '@/stores/beam'
import type { ControlButton, PickList, PickListLocation } from '@/types'
import { itemListLine } from '@/utils/itemListLine'
import { isPickListFullyPicked, pickLineTargetQty } from '@/utils/pickListProgress'

const route = useRoute()
const store = useBeamStore()
const pickListId = route.params.id.toString()

const pickList = ref(store.cache.mappers[pickListId] as PickList)
const refreshKey = ref(0)

store.$subscribe(mutation => {
	if (['patch function', 'patch object'].includes(mutation.type)) {
		refreshKey.value++
		pickList.value = store.cache.mappers[pickListId] as PickList
	}
})

onBeforeRouteLeave((to, from, next) => {
	if (pickList.value?.dirty) {
		const answer = window.confirm('You have unsaved changes. Do you want to leave without saving?')
		if (answer) {
			next()
		} else {
			next(false)
		}
	} else {
		next()
	}
})

const sortedLocations = computed((): PickListLocation[] => {
	const rows = pickList.value?.locations || []
	return [...rows].sort(
		(a, b) =>
			(a.warehouse || '').localeCompare(b.warehouse || '') || (a.item_code || '').localeCompare(b.item_code || '')
	)
})

const items = computed((): (PickListLocation & ListViewItem)[] => {
	return sortedLocations.value.map(row => {
		const line = itemListLine(row)
		return {
			...row,
			label: line.label,
			description: line.description,
			count: {
				count: row.picked_qty || 0,
				of: pickLineTargetQty(row),
			},
		}
	})
})

const updateItem = (value: PickListLocation & ListViewItem) => {
	if (!pickList.value?.locations || value.count == null) return
	const row = pickList.value.locations.find(location => location.idx === value.idx)
	if (!row || row.picked_qty === value.count.count) return
	row.picked_qty = value.count.count
	store.$patch(() => {
		const mapped = store.cache.mappers[pickListId] as PickList
		mapped.dirty = true
	})
}

const save = async () => {
	if (!pickList.value?.dirty) return
	const { data, response } = await store.update<PickList>('Pick List', pickListId, pickList.value)
	if (response.ok && data) {
		store.$patch(() => {
			pickList.value = data
			pickList.value.dirty = false
			store.cache.mappers[pickListId] = pickList.value
		})
	}
}

const submit = async () => {
	await save()
	const { data, response } = await store.submit<PickList>('Pick List', pickListId)
	if (response.ok && data) {
		store.$patch(() => {
			pickList.value = data
			pickList.value.dirty = false
			store.cache.mappers[pickListId] = pickList.value
		})
		if (data.work_order) {
			await store.refreshWorkOrderForm(data.work_order)
		}
	}
}

const controlButtons = computed((): ControlButton[] => {
	const form = pickList.value as PickList
	if (!form?.locations?.length || Number(form.docstatus) !== 0) return []

	return [
		{
			label: 'SAVE',
			disabled: items.value.length === 0,
			action: save,
		},
		{
			label: 'SUBMIT',
			disabled: !isPickListFullyPicked(form.locations),
			color: { background: 'var(--sc-success)', text: 'var(--sc-btn-color)' },
			action: submit,
		},
		{
			label: 'CANCEL',
			hidden: true,
			disabled: true,
			color: { background: 'var(--sc-beam-danger-fill)', text: 'var(--sc-btn-color)' },
			action: () => {},
		},
	]
})
</script>

<style scoped>
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
