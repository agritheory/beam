// Copyright (c) 2026, AgriTheory and contributors
// For license information, please see license.txt

import { defineStore } from 'pinia'
import { ref } from 'vue'

import { useHttpStore } from '@/stores/http'
import { useBeamStore } from '@/stores/beam'
import type {
	AwaitingLine,
	InspectionForm,
	InspectionReading,
	InspectionSubmitResult,
	LineInspection,
} from '@/types/inspection'
import type { DemandFilter } from '@/types'

const BASE = 'beam.beam.quality_inspection'
const MAX_READING_SLOTS = 10

export const useInspectionStore = defineStore('inspection', () => {
	const httpStore = useHttpStore()
	const beamStore = useBeamStore()

	const form = ref<InspectionForm | null>(null)
	const answers = ref<Record<string, string[]>>({})
	const sampleSize = ref(1)
	const readingSlots = ref<Record<string, number>>({})
	const submitting = ref(false)

	const inspectionPath = (doctype: string, name: string, row: string) =>
		`/inspect/${encodeURIComponent(doctype)}/${encodeURIComponent(name)}/${encodeURIComponent(row)}`

	const inspectionRoute = (doctype: string, name: string, row: string, state?: string) => {
		const base = inspectionPath(doctype, name, row)
		return state ? `${base}?state=${encodeURIComponent(state)}` : base
	}

	const inspectionHash = (doctype: string, name: string, row: string, state?: string) =>
		`#${inspectionRoute(doctype, name, row, state)}`

	const lines = async (doctype: string, name: string): Promise<LineInspection[]> => {
		const message = await httpStore.callMethod<LineInspection[]>(`${BASE}.get_line_inspections`, {
			doctype,
			name,
		})
		return message || []
	}

	const previewLines = async (doctype: string, items: Record<string, unknown>[]): Promise<LineInspection[]> => {
		const message = await httpStore.callMethod<LineInspection[]>(`${BASE}.preview_line_inspections`, {
			doctype,
			items: JSON.stringify(items),
		})
		return message || []
	}

	const workOrderLines = async (workOrder: string): Promise<LineInspection[]> => {
		const message = await httpStore.callMethod<LineInspection[]>(`${BASE}.get_work_order_line_inspections`, {
			work_order: workOrder,
		})
		return message || []
	}

	const awaiting = async (filters: DemandFilter, page: number): Promise<AwaitingLine[]> => {
		const payload: Record<string, string> = {}
		if (filters.status) payload.status = filters.status
		if (filters.date) payload.schedule_date = filters.date
		if (filters.user) payload.assigned = filters.user
		const message = await httpStore.callMethod<AwaitingLine[]>(`${BASE}.list_awaiting_inspection`, {
			filters: JSON.stringify(payload),
			page,
		})
		return message || []
	}

	const open = async (doctype: string, name: string, row: string) => {
		const message = await httpStore.callMethod<InspectionForm>(`${BASE}.open_inspection`, {
			doctype,
			name,
			row,
		})
		form.value = message
		sampleSize.value = form.value?.sample_size || 1
		answers.value = {}
		for (const reading of form.value?.readings || []) {
			answers.value[reading.parameter] = [...reading.values]
		}
		initReadingSlots()
	}

	const initReadingSlots = () => {
		const docSample = form.value?.sample_size || 1
		const slots: Record<string, number> = {}
		for (const reading of form.value?.readings || []) {
			if (reading.kind !== 'numeric') continue
			const filled = reading.values.filter(v => String(v ?? '').trim() !== '').length
			slots[reading.parameter] = Math.min(
				MAX_READING_SLOTS,
				Math.max(filled, docSample, 1)
			)
		}
		readingSlots.value = slots
		syncSampleSizeFromSlots()
	}

	const syncSampleSizeFromSlots = () => {
		let max = 1
		for (const reading of form.value?.readings || []) {
			if (reading.kind !== 'numeric') continue
			max = Math.max(max, readingSlots.value[reading.parameter] ?? 1)
		}
		sampleSize.value = Math.min(MAX_READING_SLOTS, max)
	}

	const slotCountFor = (parameter: string) =>
		Math.min(MAX_READING_SLOTS, Math.max(1, readingSlots.value[parameter] ?? 1))

	const addReadingSlot = (parameter: string) => {
		const next = slotCountFor(parameter) + 1
		if (next > MAX_READING_SLOTS) return
		readingSlots.value[parameter] = next
		syncSampleSizeFromSlots()
		const values = [...(answers.value[parameter] || [])]
		while (values.length < next) values.push('')
		answer(parameter, values)
	}

	const removeReadingSlot = (parameter: string, index: number) => {
		const count = slotCountFor(parameter)
		if (count <= 1 || index < 1 || index > count) return
		const values = [...(answers.value[parameter] || [])]
		while (values.length < count) values.push('')
		values.splice(index - 1, 1)
		readingSlots.value[parameter] = count - 1
		syncSampleSizeFromSlots()
		answer(parameter, values)
	}

	const answer = (parameter: string, values: string[]) => {
		answers.value[parameter] = values
		const reading = form.value?.readings.find(r => r.parameter === parameter)
		if (reading) {
			reading.values = [...values]
		}
	}

	const applySaveResult = (result: InspectionSubmitResult) => {
		if (!form.value) return
		form.value.quality_inspection = result.quality_inspection ?? result.name
		form.value.status = result.status
		form.value.can_release = result.can_release
		if (!result.readings?.length) return
		form.value.readings = result.readings
		for (const reading of result.readings) {
			answers.value[reading.parameter] = [...reading.values]
		}
		initReadingSlots()
	}

	const readingHasContent = (reading: InspectionReading, raw: string[]) => {
		if (reading.kind === 'passfail') {
			return raw[0] === 'Accepted' || raw[0] === 'Rejected'
		}
		return raw.some(v => String(v ?? '').trim() !== '')
	}

	const answersForSubmit = (options?: { onlyParameter?: string; allParameters?: boolean }) => {
		const payload: Record<string, string[]> = {}
		for (const reading of form.value?.readings || []) {
			if (options?.onlyParameter && reading.parameter !== options.onlyParameter) {
				continue
			}
			const raw = answers.value[reading.parameter] || reading.values || []
			if (!options?.onlyParameter && !options?.allParameters && !readingHasContent(reading, raw)) {
				continue
			}
			if (reading.kind === 'numeric') {
				const count = slotCountFor(reading.parameter)
				const values = raw.slice(0, count)
				while (values.length < count) values.push('')
				payload[reading.parameter] = values
			} else {
				payload[reading.parameter] = [...raw]
			}
		}
		return payload
	}

	const discardDraft = async () => {
		if (!form.value) {
			throw new Error('No inspection form open')
		}
		submitting.value = true
		try {
			const message = await httpStore.callMethod<InspectionForm>(`${BASE}.discard_inspection_draft`, {
				doctype: form.value.reference_type,
				name: form.value.reference_name,
				row: form.value.row,
			})
			form.value = message
			sampleSize.value = form.value?.sample_size || 1
			answers.value = {}
			for (const reading of form.value?.readings || []) {
				answers.value[reading.parameter] = [...reading.values]
			}
			initReadingSlots()
		} finally {
			submitting.value = false
		}
	}

	const saveDraft = async (onlyParameter?: string): Promise<InspectionSubmitResult> => {
		if (!form.value) {
			throw new Error('No inspection form open')
		}
		submitting.value = true
		try {
			const result = await httpStore.callMethod<InspectionSubmitResult>(`${BASE}.save_inspection_draft`, {
				doctype: form.value.reference_type,
				name: form.value.reference_name,
				row: form.value.row,
				sample_size: sampleSize.value,
				answers: JSON.stringify(answersForSubmit({ onlyParameter })),
			})
			applySaveResult(result)
			return result
		} finally {
			submitting.value = false
		}
	}

	const submit = async (): Promise<InspectionSubmitResult & { photosPending: number }> => {
		if (!form.value) {
			throw new Error('No inspection form open')
		}
		submitting.value = true
		try {
			const result = await httpStore.callMethod<InspectionSubmitResult>(`${BASE}.submit_inspection`, {
				doctype: form.value.reference_type,
				name: form.value.reference_name,
				row: form.value.row,
				sample_size: sampleSize.value,
				answers: JSON.stringify(answersForSubmit({ allParameters: true })),
			})
			const upload = await beamStore.uploadFiles(
				'Quality Inspection',
				result.name,
				beamStore.camera.pendingPhotos
			)
			beamStore.setPendingPhotos(upload?.failed ?? [])
			return {
				...result,
				photosPending: beamStore.camera.pendingPhotos.length,
			}
		} finally {
			submitting.value = false
		}
	}

	const retryPhotos = async () => {
		if (!form.value?.quality_inspection) return { photosPending: 0 }
		const upload = await beamStore.uploadFiles(
			'Quality Inspection',
			form.value.quality_inspection,
			beamStore.camera.pendingPhotos
		)
		beamStore.setPendingPhotos(upload?.failed ?? [])
		return { photosPending: beamStore.camera.pendingPhotos.length }
	}

	const release = async (): Promise<string> => {
		if (!form.value?.quality_inspection) {
			throw new Error('No inspection to release')
		}
		return httpStore.callMethod<string>(`${BASE}.release_from_quarantine`, {
			quality_inspection: form.value.quality_inspection,
		})
	}

	const reinspect = async () => {
		if (!form.value?.quality_inspection) return
		const message = await httpStore.callMethod<InspectionForm>(`${BASE}.reinspect`, {
			quality_inspection: form.value.quality_inspection,
		})
		form.value = message
		sampleSize.value = form.value.sample_size || 1
		answers.value = {}
		for (const reading of form.value.readings) {
			answers.value[reading.parameter] = [...reading.values]
		}
		initReadingSlots()
	}

	const readingRows = (): InspectionReading[] => form.value?.readings || []

	return {
		form,
		answers,
		sampleSize,
		readingSlots,
		submitting,
		MAX_READING_SLOTS,
		initReadingSlots,
		slotCountFor,
		addReadingSlot,
		removeReadingSlot,
		answersForSubmit,
		inspectionPath,
		inspectionRoute,
		inspectionHash,
		lines,
		previewLines,
		workOrderLines,
		awaiting,
		open,
		answer,
		saveDraft,
		discardDraft,
		submit,
		retryPhotos,
		release,
		reinspect,
		readingRows,
	}
})
