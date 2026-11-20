// Copyright (c) 2026, AgriTheory and contributors
// For license information, please see license.txt

import { ref, shallowRef } from 'vue'

import { useBeamStore } from '@/stores/beam'

declare const frappe: any

const SELECTED_KEY = 'beam_selected_workstation'

type TabletSettings = {
	require_user_scan: number
	user_scan_idle_minutes: number
}

const settingsCache: Record<string, TabletSettings> = {}

export const scanGateActive = ref(false)
export const scanGateMessage = ref('')
const pendingScanContinuation = shallowRef<(() => Promise<void>) | null>(null)

function lastScanKey(workstation: string): string {
	return `beam_workstation_scan_${encodeURIComponent(workstation)}`
}

export function getSelectedWorkstation(): string | null {
	if (typeof localStorage === 'undefined') return null
	return localStorage.getItem(SELECTED_KEY)
}

export function setSelectedWorkstation(name: string | null): void {
	if (typeof localStorage === 'undefined') return
	if (name) localStorage.setItem(SELECTED_KEY, name)
	else localStorage.removeItem(SELECTED_KEY)
}

export function getLastScanTimestamp(workstation: string): number | null {
	if (typeof localStorage === 'undefined') return null
	const raw = localStorage.getItem(lastScanKey(workstation))
	if (!raw) return null
	const parsed = Number(raw)
	return Number.isFinite(parsed) ? parsed : null
}

export function setLastScanTimestamp(workstation: string, ms: number): void {
	if (typeof localStorage === 'undefined') return
	localStorage.setItem(lastScanKey(workstation), String(ms))
}

export async function loadTabletSettings(workstation: string): Promise<TabletSettings> {
	if (settingsCache[workstation]) return settingsCache[workstation]
	const store = useBeamStore()
	const data = await store.getWorkstationTabletSettings(workstation)
	settingsCache[workstation] = data
	return data
}

export function isIdleScanRequired(settings: TabletSettings, workstation: string): boolean {
	if (!settings.require_user_scan) return false
	const last = getLastScanTimestamp(workstation)
	if (last === null) return true
	const idleMs = (settings.user_scan_idle_minutes || 15) * 60 * 1000
	return Date.now() - last > idleMs
}

export async function runWithTabletScanGate(
	workstation: string | undefined | null,
	action: () => Promise<void>
): Promise<void> {
	if (!workstation) {
		await action()
		return
	}
	const settings = await loadTabletSettings(workstation)
	if (!isIdleScanRequired(settings, workstation)) {
		await action()
		return
	}

	scanGateMessage.value = 'Scan your badge to continue'
	scanGateActive.value = true

	await new Promise<void>((resolve, reject) => {
		pendingScanContinuation.value = async () => {
			scanGateActive.value = false
			scanGateMessage.value = ''
			pendingScanContinuation.value = null
			try {
				await action()
				resolve()
			} catch (error) {
				reject(error)
			}
		}
	})
}

export async function handleTabletUserScan(barcode: string): Promise<boolean> {
	if (!pendingScanContinuation.value) return false
	const toast = (await import('@/utils/toast.js')).useBeamToast()
	try {
		await frappe.xcall('beam.beam.scan.user_login.scan_login', { barcode })
		const ws = getSelectedWorkstation()
		if (ws) setLastScanTimestamp(ws, Date.now())
		const continuation = pendingScanContinuation.value
		if (continuation) await continuation()
		return true
	} catch (error) {
		toast.error((error as Error)?.message || 'Badge scan failed')
		return true
	}
}

export function clearTabletScanGate(): void {
	scanGateActive.value = false
	scanGateMessage.value = ''
	pendingScanContinuation.value = null
}

export function workstationForSelectedStation(): string | null {
	return getSelectedWorkstation()
}