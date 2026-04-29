<template>
	<Navbar>
		<template #title>
			<h1>{{ operation.operation || 'Operation' }}</h1>
		</template>
		<template #navbaraction>
			<RouterLink :to="{ name: 'work_order', params: { id: workOrderId } }">Back</RouterLink>
		</template>
	</Navbar>
	<div class="container">
		<div class="box metadata-box">
			<p class="operation-title">{{ operation.operation || 'Operation' }}</p>
			<p class="operation-station">{{ operation.workstation || 'Workstation not set' }}</p>
			<p class="operation-description">{{ operation.description || 'No operation description.' }}</p>
			<p v-if="sequenceBlockedBy" class="sequence-warning">Complete {{ sequenceBlockedBy }} before finishing.</p>
		</div>
		<div class="box timer-box">
			<b class="timer-value">{{ elapsedTime }}</b>
			<p class="status-text">{{ statusLabel }}</p>
			<p class="qty-info">To complete: {{ remainingQty }} units</p>
			<p v-if="hasActiveConflict" class="sequence-warning">
				You already have an active job: {{ activeJobCardForEmployee }}
			</p>
			<p v-if="actionError" class="action-error">{{ actionError }}</p>
			<div class="actions">
				<button
					:disabled="actionsDisabled || isCompleted || Boolean(sequenceBlockedBy) || hasActiveConflict || !canToggle"
					@click="toggleOperation">
					{{ toggleLabel }}
				</button>
				<button :disabled="actionsDisabled || !isQtyCompleted" @click="finishOperation">Finish</button>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import { useBeamStore } from '@/stores/beam'
import { useBeamToast } from '@/utils/toast'
import type { JobCard, JobCardTimeLog, WorkOrder, WorkOrderOperation } from '@/types'

declare const frappe: any

type TimeLog = JobCardTimeLog

interface RouteParams {
	id?: string
	operationId?: string
}

const route = useRoute()
const store = useBeamStore()
const toast = useBeamToast()
const workOrderId = computed((): string => String((route.params as RouteParams).id || ''))
const operationId = computed((): string => String((route.params as RouteParams).operationId || ''))
const workOrder = computed(() => store.form as Partial<WorkOrder>)

const operation = ref<Partial<WorkOrderOperation>>({})
const jobCard = ref<Partial<JobCard>>({})
const jobCardName = ref<string>('')
const elapsedSeconds = ref<number>(0)
const isBusy = ref<boolean>(false)
const isRefreshing = ref<boolean>(false)
const actionError = ref<string>('')
const hasLoadError = ref<boolean>(false)
let timerHandle: ReturnType<typeof setInterval> | null = null

const isCompleted = computed((): boolean => (jobCard.value.status || '') === 'Completed')

const activeTimeLog = computed((): TimeLog | null => {
	const logs: TimeLog[] = (jobCard.value.time_logs as TimeLog[]) || []
	const last = logs[logs.length - 1]
	return last && !last.to_time ? last : null
})

const isRunning = computed((): boolean => {
	if (isCompleted.value) return false
	return (jobCard.value.status || '') === 'Work In Progress' && Boolean(activeTimeLog.value)
})

const sequenceBlockedBy = computed((): string => {
	const operations: Partial<WorkOrderOperation>[] = workOrder.value.operations || []
	if (!operations.length) return ''

	const current = operations.find((op: Partial<WorkOrderOperation>) => op.name === operationId.value)
	if (!current || !current.idx) return ''

	const totalQty: number = workOrder.value.qty || 0
	const previous = operations
		.filter((op: Partial<WorkOrderOperation>) => Number(op.idx || 0) < Number(current.idx || 0))
		.find((op: Partial<WorkOrderOperation>) => (op.completed_qty || 0) < totalQty)

	return previous?.operation || ''
})

const elapsedTime = computed((): string => {
	const date = new Date(0)
	date.setSeconds(Math.max(0, Math.floor(elapsedSeconds.value)))
	return isNaN(date.getTime()) ? '00:00:00' : date.toISOString().substring(11, 19)
})

const statusLabel = computed((): string => jobCard.value.status || '')
const activeJobCardForEmployee = computed((): string => jobCard.value.active_job_card_for_employee || '')
const hasActiveConflict = computed((): boolean => Boolean(jobCard.value.active_job_card_for_employee))
const isSubmitted = computed((): boolean => jobCard.value.docstatus !== 0)
const isQtyCompleted = computed((): boolean => {
	const completed = Number(jobCard.value.total_completed_qty || 0)
	const required = Number(jobCard.value.for_quantity || 0)
	return completed >= required && required > 0
})

const actionsDisabled = computed(
	(): boolean => isBusy.value || hasLoadError.value || !jobCardName.value || isSubmitted.value
)
const toggleLabel = computed((): string => (isRunning.value ? 'Pause' : 'Start'))
const canToggle = computed((): boolean => !isQtyCompleted.value)
const remainingQty = computed((): number =>
	Math.max(0, Number(jobCard.value.for_quantity || 0) - Number(jobCard.value.total_completed_qty || 0))
)

const startTicking = (): void => {
	if (timerHandle) return
	timerHandle = setInterval((): void => {
		elapsedSeconds.value += 1
	}, 1000)
}

const stopTicking = () => {
	if (!timerHandle) return
	clearInterval(timerHandle)
	timerHandle = null
}

const applyJobCard = (card: Partial<JobCard> | null | undefined): void => {
	if (!card) {
		jobCard.value = {}
		elapsedSeconds.value = 0
		stopTicking()
		return
	}

	jobCard.value = card
	if (isRunning.value && !hasActiveConflict.value) {
		const closedMins = (jobCard.value.time_logs || [])
			.filter((log: TimeLog) => log.to_time)
			.reduce((sum: number, log: TimeLog) => sum + (log.time_in_mins || 0), 0)

		let activeMins = 0
		if (activeTimeLog.value?.from_time) {
			const fromTime = new Date(activeTimeLog.value.from_time).getTime()
			const serverNowStr = frappe.datetime.now_datetime()
			const serverNowMs = new Date(serverNowStr).getTime()
			activeMins = (serverNowMs - fromTime) / (1000 * 60)
		}

		const totalMins = closedMins + activeMins
		elapsedSeconds.value = Math.max(0, Math.floor(totalMins * 60))
		startTicking()
	} else {
		const totalMins = (jobCard.value.time_logs || []).reduce(
			(sum: number, log: TimeLog) => sum + (log.time_in_mins || 0),
			0
		)
		elapsedSeconds.value = hasActiveConflict.value ? 0 : Math.max(0, Math.floor(totalMins * 60))
		stopTicking()
	}
}

const refreshJobCard = async (): Promise<void> => {
	if (isRefreshing.value) return
	isRefreshing.value = true
	hasLoadError.value = false
	actionError.value = ''

	let jobList: Partial<JobCard>[] = []
	try {
		jobList = await store.getAll<Partial<JobCard>>('Job Card', {
			filters: JSON.stringify([
				['operation_id', '=', operationId.value],
				['work_order', '=', workOrderId.value],
			]),
		})
	} catch (error) {
		hasLoadError.value = true
		jobCardName.value = ''
		jobCard.value = {}
		elapsedSeconds.value = 0
		stopTicking()
		const message = (error as Error)?.message || 'Unknown error'
		actionError.value = message
		toast.error(message)
		isRefreshing.value = false
		return
	}

	if (!jobList) {
		hasLoadError.value = true
		jobCardName.value = ''
		jobCard.value = {}
		elapsedSeconds.value = 0
		stopTicking()
		actionError.value = 'Unknown error'
		toast.error(actionError.value)
		isRefreshing.value = false
		return
	}

	if (jobList.length > 0 && jobList[0].name) {
		jobCardName.value = jobList[0].name
		try {
			const res = await store.getJobCard(jobCardName.value)
			if (!res) {
				hasLoadError.value = true
				jobCardName.value = ''
				jobCard.value = {}
				elapsedSeconds.value = 0
				stopTicking()
				actionError.value = 'Unknown error'
				toast.error(actionError.value)
				isRefreshing.value = false
				return
			}

			applyJobCard(res)
		} catch (error) {
			hasLoadError.value = true
			jobCardName.value = ''
			jobCard.value = {}
			elapsedSeconds.value = 0
			stopTicking()
			const message = (error as Error)?.message || 'Unknown error'
			actionError.value = message
			toast.error(message)
			isRefreshing.value = false
			return
		}
	} else {
		jobCardName.value = ''
		jobCard.value = {}
		elapsedSeconds.value = 0
		stopTicking()
	}

	isRefreshing.value = false
}

const syncFromBackendOnReturn = async (): Promise<void> => {
	if (document.visibilityState !== 'visible') return
	if (isBusy.value) return
	await refreshJobCard()
}

onMounted(async (): Promise<void> => {
	operation.value =
		workOrder.value.operations?.find((op: Partial<WorkOrderOperation>) => op.name === operationId.value) || {}
	await refreshJobCard()
	document.addEventListener('visibilitychange', syncFromBackendOnReturn)
	window.addEventListener('focus', syncFromBackendOnReturn)
})

onUnmounted((): void => {
	document.removeEventListener('visibilitychange', syncFromBackendOnReturn)
	window.removeEventListener('focus', syncFromBackendOnReturn)
	stopTicking()
})

const toggleOperation = async (): Promise<void> => {
	if (!jobCardName.value || isBusy.value || isCompleted.value) return

	isBusy.value = true
	actionError.value = ''
	try {
		await refreshJobCard()
		if (!jobCardName.value || isCompleted.value) return

		if (isRunning.value) {
			const remainingQty: number = Math.max(
				0,
				Number(jobCard.value.for_quantity || 0) - Number(jobCard.value.total_completed_qty || 0)
			)
			const defaultQty: string = String(remainingQty)
			const input: string | null = window.prompt('Completed quantity in this session', defaultQty)
			if (input === null) {
				isBusy.value = false
				return
			}

			const completedQty: number = Number(input)
			if (!Number.isFinite(completedQty) || completedQty < 0) {
				actionError.value = 'Invalid quantity'
				toast.error('Invalid quantity')
				isBusy.value = false
				return
			}

			const card = await store.pauseJobCard(jobCardName.value, completedQty)
			applyJobCard(card)
		} else {
			const card = await store.startJobCard(jobCardName.value)
			applyJobCard(card)
		}
	} catch (error) {
		const message = (error as Error)?.message || 'Unknown error'
		actionError.value = message
		toast.error(message)
	} finally {
		isBusy.value = false
	}
}

const finishOperation = async (): Promise<void> => {
	if (!jobCardName.value || isBusy.value || !isQtyCompleted.value) return

	isBusy.value = true
	actionError.value = ''
	try {
		const currentQty = Number(jobCard.value.total_completed_qty || 0)
		const card = await store.finishJobCard(jobCardName.value, currentQty)
		applyJobCard(card)
	} catch (error) {
		const message = (error as Error)?.message || 'Unknown error'
		actionError.value = message
		toast.error(message)
	} finally {
		isBusy.value = false
	}
}
</script>

<style scoped>
.container {
	display: grid;
	grid-template-columns: 1fr;
	gap: 0.5rem;
	padding: 0.25rem 0.5rem;
	width: 100%;
	box-sizing: border-box;
}

.box {
	padding: 0.9rem;
	margin: 0;
	font-size: 1rem;
	border: 2px solid gray;
	outline: 2px solid transparent;
	min-width: 0;
	box-sizing: border-box;
}

.metadata-box {
	display: grid;
	gap: 0.5rem;
}

.operation-title {
	margin: 0;
	font-weight: 700;
	font-size: 1.1rem;
}

.operation-station {
	margin: 0;
	font-size: 0.9rem;
	opacity: 0.8;
}

.operation-description {
	margin: 0;
	line-height: 1.35;
}

.sequence-warning {
	margin: 0;
	font-size: 0.85rem;
	color: #9a6a00;
}

.timer-box {
	text-align: center;
	display: grid;
	gap: 0.45rem;
}

.timer-value {
	margin: 0;
	display: flex;
	justify-content: center;
	align-items: center;
	font-size: clamp(1.75rem, 10vw, 2.25rem);
	letter-spacing: 0.08em;
}

.status-text {
	margin: 0;
	font-size: 0.85rem;
	opacity: 0.8;
}

.qty-info {
	margin: 0;
	font-size: 0.9rem;
	font-weight: 600;
	color: #333;
}

.action-error {
	margin: 0;
	font-size: 0.85rem;
	color: #b30000;
}

.actions {
	display: grid;
	grid-template-columns: 1fr;
	gap: 0.4rem;
}

button {
	width: 100%;
	padding: 0.9rem 0.8rem;
	font-size: 1rem;
	border: 1px solid #6c6c6c;
	background: #f3f3f3;
	color: #111;
}

button:disabled {
	opacity: 0.55;
}

@media (min-width: 760px) {
	.actions {
		grid-template-columns: repeat(3, 1fr);
	}
}
</style>
