<template>
	<Navbar @click="onNavbarPrimary">
		<template #title>
			<h1>{{ titleText }}</h1>
		</template>
		<template #navbaraction>
			<span v-if="selectedStation">Change station</span>
			<RouterLink v-else :to="{ name: 'home' }">Home</RouterLink>
		</template>
	</Navbar>

	<template v-if="selectedStation">
		<ListView :items="queueItems" :loaded="queueLoaded" empty-text="Nothing to run at this station" />
	</template>
	<template v-else>
		<ListView :items="pickerItems" :loaded="pickerLoaded" empty-text="No workstations" @select="onPickStation" />
	</template>
</template>

<script setup lang="ts">
import type { ListViewItem } from '@/types/stonecrop.js'
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import { getSelectedWorkstation, setSelectedWorkstation } from '@/composables/useWorkstationTablet'
import { useBeamStore } from '@/stores/beam'
import type { Workstation } from '@/types'

const route = useRoute()
const router = useRouter()
const store = useBeamStore()
const selectedStation = ref<string | null>(getSelectedWorkstation())

const stationFromRoute = (): string | null => {
	const raw = route.params.station
	if (typeof raw !== 'string' || !raw.trim()) return null
	try {
		return decodeURIComponent(raw)
	} catch {
		return raw
	}
}

const applySelectedStation = (name: string | null) => {
	selectedStation.value = name
	if (name) setSelectedWorkstation(name)
	else setSelectedWorkstation(null)
}
const pickerItems = ref<ListViewItem[]>([])
const pickerLoaded = ref(false)
const queueItems = ref<ListViewItem[]>([])
const queueLoaded = ref(false)

const titleText = computed(() => selectedStation.value || 'Workstations')

const loadPicker = async () => {
	pickerLoaded.value = false
	const stations = await store.getAll<Workstation>('Workstation', {
		fields: JSON.stringify(['name', 'workstation_type', 'plant_floor']),
		order_by: 'creation asc',
	})

	pickerItems.value = stations.map(row => ({
		...row,
		barcode: row.name,
		label: row.name,
		description: [row.workstation_type, row.plant_floor].filter(Boolean).join(' · '),
	}))
	pickerLoaded.value = true
}

const loadQueue = async () => {
	if (!selectedStation.value) return
	queueLoaded.value = false
	const rows = await store.getWorkstationQueue(selectedStation.value)
	queueItems.value = rows.map(row => ({
		barcode: row.job_card,
		label: row.operation,
		description: `${row.item_name} · qty ${row.work_order_qty}`,
		linkComponent: 'ListAnchor',
		route: `#/work_order/${row.work_order}`,
	}))
	queueLoaded.value = true
}

const onPickStation = (item: ListViewItem) => {
	const name = String(item.barcode || item.label || '')
	if (!name) return
	void router.push({ name: 'workstation_queue', params: { station: name } })
}

const changeStation = async (): Promise<void> => {
	queueItems.value = []
	applySelectedStation(null)
	await router.push({ name: 'workstation' })
	await loadPicker()
}

const onNavbarPrimary = (): void => {
	if (selectedStation.value) void changeStation()
}

const syncStationView = async () => {
	const fromRoute = stationFromRoute()
	if (fromRoute) {
		applySelectedStation(fromRoute)
		await loadQueue()
		return
	}
	const saved = getSelectedWorkstation()
	if (saved) {
		await router.replace({ name: 'workstation_queue', params: { station: saved } })
		return
	}
	applySelectedStation(null)
	await loadPicker()
}

onMounted(() => {
	void syncStationView()
})

watch(
	() => [route.name, route.params.station] as const,
	() => {
		void syncStationView()
	}
)
</script>
