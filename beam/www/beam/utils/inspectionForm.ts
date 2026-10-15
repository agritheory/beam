// Copyright (c) 2026, AgriTheory and contributors
// For license information, please see license.txt

import type { Router, RouteLocationRaw } from 'vue-router'

import type { InspectionReading } from '@/types/inspection'

export type InspectionSourceOptions = {
	from?: string
	purchaseOrder?: string | null
}

export function inspectionSourceRoute(
	referenceType: string,
	referenceName: string,
	options: InspectionSourceOptions = {}
): string | RouteLocationRaw {
	if (options.from) {
		const raw = options.from.trim()
		return raw.startsWith('#') ? raw.slice(1) : raw
	}

	switch (referenceType) {
		case 'Purchase Receipt':
			return {
				name: 'purchase-receipt',
				params: { id: options.purchaseOrder || referenceName },
			}
		case 'Delivery Note':
			return { name: 'delivery-note', query: { id: referenceName } }
		case 'Stock Entry':
			return { name: 'move' }
		default:
			return { name: 'inspect' }
	}
}

export function navigateAfterInspection(router: Router, target: string | RouteLocationRaw) {
	if (typeof target === 'string') {
		const path = target.startsWith('/') ? target : `/${target}`
		return router.push(path)
	}
	return router.push(target)
}

export function inspectionFieldId(parameter: string, index = 1): string {
	return `qi-${parameter.replace(/\W+/g, '-')}-${index}`
}

export function parameterHasInput(reading: InspectionReading): boolean {
	if (reading.kind === 'passfail') {
		return reading.values[0] === 'Accepted' || reading.values[0] === 'Rejected'
	}
	if (reading.kind === 'numeric') {
		return reading.values.some(v => String(v ?? '').trim() !== '')
	}
	return String(reading.values[0] ?? '').trim() !== ''
}

export function firstIncompleteParameter(readings: InspectionReading[]): string | undefined {
	for (const reading of readings) {
		if (!parameterHasInput(reading)) return reading.parameter
	}
	return readings[0]?.parameter
}

export function focusParameterInput(parameter: string, kind: InspectionReading['kind']) {
	if (kind === 'passfail') {
		const sections = document.querySelectorAll<HTMLElement>('[data-inspection-parameter]')
		const section = [...sections].find(el => el.dataset.inspectionParameter === parameter)
		const btn = section?.querySelector<HTMLButtonElement>('.passfail-btn')
		btn?.focus()
		return
	}
	document.getElementById(inspectionFieldId(parameter, 1))?.focus()
}
