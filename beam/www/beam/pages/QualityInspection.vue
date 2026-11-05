<template>
	<Navbar>
		<template #title>
			<h1>{{ inspection.form?.item_name || 'Inspect' }}</h1>
			<span v-if="statusLabel" class="status-pill">{{ statusLabel }}</span>
		</template>
		<template #navbaraction>
			<RouterLink :to="backRoute">Back</RouterLink>
		</template>
	</Navbar>

	<div v-if="inspection.form" class="inspection-shell">
		<div class="inspection-list">
			<InspectionParameterPanel
				v-for="reading in inspection.form.readings"
				:key="reading.parameter"
				:reading="reading"
				:editable="Boolean(inspection.form.editable)"
				:expanded="expandedParameter === reading.parameter"
				:slot-count="inspection.slotCountFor(reading.parameter)"
				:max-slots="inspection.MAX_READING_SLOTS"
				:saving="savingParameter === reading.parameter"
				@toggle="toggleParameter(reading.parameter)"
				@add-reading="inspection.addReadingSlot(reading.parameter)"
				@remove-reading="index => inspection.removeReadingSlot(reading.parameter, index)"
				@save="() => saveParameter(reading.parameter)"
				@answer="values => inspection.answer(reading.parameter, values)" />
		</div>

		<p v-if="!inspection.form.editable && !inspection.form.correction" class="readonly-note beam_copy">
			Correct this inspection at the desk.
		</p>
	</div>

	<ControlButtons :buttons="buttons" />
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import ControlButtons from '@/components/ControlButtons.vue'
import InspectionParameterPanel from '@/components/InspectionParameterPanel.vue'
import { useBeamStore } from '@/stores/beam'
import { useInspectionStore } from '@/stores/inspection'
import type { ControlButton } from '@/types'
import {
	firstIncompleteParameter,
	focusParameterInput,
	inspectionSourceRoute,
	navigateAfterInspection,
} from '@/utils/inspectionForm'

const route = useRoute()
const router = useRouter()
const inspection = useInspectionStore()
const beamStore = useBeamStore()

const expandedParameter = ref<string | null>(null)
const savingParameter = ref<string | null>(null)
const expandInitialized = ref(false)

const doctype = computed(() => decodeURIComponent(route.params.doctype as string))
const docname = computed(() => decodeURIComponent(route.params.name as string))
const row = computed(() => decodeURIComponent(route.params.row as string))

const sourceOptions = computed(() => ({
	from: route.query.from as string | undefined,
	purchaseOrder: inspection.form?.purchase_order,
}))

const backRoute = computed(() => inspectionSourceRoute(doctype.value, docname.value, sourceOptions.value))

const returnToSource = async () => {
	const form = inspection.form
	if (!form) return
	await navigateAfterInspection(
		router,
		inspectionSourceRoute(form.reference_type, form.reference_name, {
			from: sourceOptions.value.from,
		})
	)
}

const statusLabel = computed(() => {
	const status = inspection.form?.status
	if (!status || status === 'needed') return ''
	return status
})

const setInitialExpanded = () => {
	const readings = inspection.form?.readings
	if (!readings?.length) {
		expandedParameter.value = null
		return
	}
	expandedParameter.value = firstIncompleteParameter(readings) ?? readings[0].parameter
	expandInitialized.value = true
}

const toggleParameter = (parameter: string) => {
	expandedParameter.value = expandedParameter.value === parameter ? null : parameter
}

const saveParameter = async (parameter: string) => {
	if (!inspection.form?.editable || savingParameter.value) return

	savingParameter.value = parameter
	try {
		await inspection.saveDraft(parameter)
		const readings = inspection.form?.readings || []
		const index = readings.findIndex(r => r.parameter === parameter)
		expandedParameter.value = null
		await nextTick()
		const next = index >= 0 ? readings[index + 1] : undefined
		if (next) {
			expandedParameter.value = next.parameter
			await nextTick()
			focusParameterInput(next.parameter, next.kind)
		}
	} finally {
		savingParameter.value = null
	}
}

watch(
	() => inspection.form?.readings,
	readings => {
		if (!readings?.length) {
			expandedParameter.value = null
			expandInitialized.value = false
			return
		}
		if (!expandInitialized.value) {
			setInitialExpanded()
		}
	},
	{ immediate: true }
)

watch([doctype, docname, row], () => {
	expandInitialized.value = false
})

onMounted(async () => {
	expandInitialized.value = false
	await inspection.open(doctype.value, docname.value, row.value)
})

const footerBusy = ref(false)

const buttons = computed((): ControlButton[] => {
	const form = inspection.form
	if (!form) return []

	const out: ControlButton[] = []
	const successColor = { background: 'var(--sc-success)', text: 'var(--sc-btn-color)' }
	const dangerColor = { background: 'var(--sc-beam-danger-fill)', text: 'var(--sc-btn-color)' }

	if (form.editable) {
		out.push({
			label: 'SUBMIT',
			disabled: footerBusy.value,
			color: successColor,
			action: async () => {
				footerBusy.value = true
				try {
					await inspection.submit()
					await returnToSource()
				} finally {
					footerBusy.value = false
				}
			},
		})
		out.push({
			label: 'SAVE',
			disabled: footerBusy.value,
			action: async () => {
				footerBusy.value = true
				try {
					await inspection.saveDraft()
				} finally {
					footerBusy.value = false
				}
			},
		})
		if (form.quality_inspection) {
			out.push({
				label: 'DISCARD',
				disabled: footerBusy.value,
				color: dangerColor,
				action: async () => {
					footerBusy.value = true
					try {
						await inspection.discardDraft()
						await returnToSource()
					} finally {
						footerBusy.value = false
					}
				},
			})
		}
	}

	if (form.can_release) {
		out.push({
			label: 'RELEASE',
			color: { background: 'var(--sc-success)', text: 'var(--sc-btn-color)' },
			action: async () => {
				const seName = await inspection.release()
				await router.push({ name: 'move', query: { id: seName } })
			},
		})
	}

	if (form.quality_inspection && beamStore.camera.pendingPhotos.length > 0) {
		out.push({
			label: 'RETRY PHOTOS',
			action: async () => {
				await inspection.retryPhotos()
			},
		})
	}

	return out
})
</script>

<style scoped>
.inspection-shell {
	margin: 0.5rem var(--sc-list-margin) 5rem;
	border: 1px solid var(--sc-row-border-color);
	background: var(--sc-btn-color);
	font-family: var(--sc-font-family);
}

.inspection-list {
	margin: 0;
}

.status-pill {
	font-size: 0.8125rem;
	font-weight: 600;
	color: var(--sc-primary-text-color);
	margin-left: 0.5rem;
}

.readonly-note {
	margin: 0;
	padding: 1rem var(--sc-list-margin);
	border-top: 1px solid var(--sc-row-border-color);
	color: var(--sc-alert);
}
</style>
