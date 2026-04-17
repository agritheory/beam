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
			<p v-if="actionError" class="action-error">{{ actionError }}</p>
			<div class="actions">
				<button :disabled="actionsDisabled || isRunning || isCompleted" @click="startOperation">Start</button>
				<button :disabled="actionsDisabled || !isRunning || isCompleted" @click="pauseOperation">Pause</button>
				<button :disabled="actionsDisabled || isCompleted || Boolean(sequenceBlockedBy)" @click="finishOperation">Finish</button>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'

import { useBeamStore } from '@/stores/beam'
import type { JobCard, WorkOrder, WorkOrderOperation } from '@/types'
import { useBeamToast } from '@/utils/toast'

const route = useRoute()
const store = useBeamStore()
const toast = useBeamToast()
const workOrderId = computed(() => String((route.params as { id?: string }).id || ''))
const operationId = computed(() => String((route.params as { operationId?: string }).operationId || ''))
const workOrder = computed(() => store.form as Partial<WorkOrder>)

const operation = ref<Partial<WorkOrderOperation>>({})
const jobCard = ref<Partial<JobCard>>({})
const jobCardName = ref('')
const timerNow = ref(Date.now())
const isBusy = ref(false)
const actionError = ref('')
const hasLoadError = ref(false)
let timerHandle: ReturnType<typeof setInterval> | null = null

const isCompleted = computed(() => ['Complete', 'Completed'].includes(jobCard.value.status || ''))

const isRunning = computed(() => {
	if (!jobCard.value || !jobCard.value.started_time) return false
	if (isCompleted.value) return false
	return (jobCard.value.status || '') === 'Work In Progress'
})

const sequenceBlockedBy = computed(() => {
	const operations = workOrder.value.operations || []
	if (!operations.length) return ''

	const current = operations.find((op: Partial<WorkOrderOperation>) => op.name === operationId.value)
	if (!current || !current.idx) return ''

	const totalQty = workOrder.value.qty || 0
	const previous = operations
		.filter((op: Partial<WorkOrderOperation>) => Number(op.idx || 0) < Number(current.idx || 0))
		.find((op: Partial<WorkOrderOperation>) => (op.completed_qty || 0) < totalQty)

	return previous?.operation || ''
})

const elapsedSeconds = computed(() => {
	const accumulated = Math.max(0, Math.floor(Number(jobCard.value?.current_time || 0)))
	if (!isRunning.value || !jobCard.value?.started_time) return accumulated

	const startedAt = new Date(jobCard.value.started_time).getTime()
	if (isNaN(startedAt)) return accumulated

	const runningDelta = Math.max(0, Math.floor((timerNow.value - startedAt) / 1000))
	return accumulated + runningDelta
})

const elapsedTime = computed(() => {
	const date = new Date(0)
	date.setSeconds(elapsedSeconds.value)
	return isNaN(date.getTime()) ? '00:00:00' : date.toISOString().substring(11, 19)
})

const statusLabel = computed(() => {
	if (isCompleted.value) return 'Completed'
	return isRunning.value ? 'In Progress' : 'Paused'
})

const actionsDisabled = computed(() => isBusy.value || hasLoadError.value || !jobCardName.value)

const startTicking = () => {
	if (timerHandle) return
	timerHandle = setInterval(() => {
		timerNow.value = Date.now()
	}, 1000)
}

const stopTicking = () => {
	if (!timerHandle) return
	clearInterval(timerHandle)
	timerHandle = null
}

const refreshJobCard = async () => {
	hasLoadError.value = false
	actionError.value = ''

	let jobList: JobCard[] = []
	try {
		jobList = await store.getAll<JobCard>('Job Card', {
			filters: JSON.stringify([
				['operation_id', '=', operationId.value],
				['work_order', '=', workOrderId.value],
			]),
		})
	} catch (error) {
		hasLoadError.value = true
		jobCardName.value = ''
		jobCard.value = {}
		stopTicking()
		const message = (error as Error)?.message || 'Unknown error'
		actionError.value = message
		toast.error(message)
		return
	}

	if (!jobList) {
		hasLoadError.value = true
		jobCardName.value = ''
		jobCard.value = {}
		stopTicking()
		actionError.value = 'Unknown error'
		toast.error(actionError.value)
		return
	}

	if (jobList.length > 0 && jobList[0].name) {
		jobCardName.value = jobList[0].name
		try {
			const res = await store.getOne<JobCard>('Job Card', jobCardName.value)
			if (!res) {
				hasLoadError.value = true
				jobCardName.value = ''
				jobCard.value = {}
				stopTicking()
				actionError.value = 'Unknown error'
				toast.error(actionError.value)
				return
			}

			jobCard.value = res
		} catch (error) {
			hasLoadError.value = true
			jobCardName.value = ''
			jobCard.value = {}
			stopTicking()
			const message = (error as Error)?.message || 'Unknown error'
			actionError.value = message
			toast.error(message)
			return
		}
	} else {
		jobCardName.value = ''
		jobCard.value = {}
	}

	timerNow.value = Date.now()
	if (isRunning.value) {
		startTicking()
	} else {
		stopTicking()
	}
}

onMounted(async () => {
	operation.value = workOrder.value.operations?.find((op: Partial<WorkOrderOperation>) => op.name === operationId.value) || {}
	await refreshJobCard()
})

onUnmounted(() => {
	stopTicking()
})

const startOperation = async () => {
	if (!jobCardName.value || isBusy.value || isRunning.value || isCompleted.value) return

	isBusy.value = true
	actionError.value = ''
	try {
		await store.startJobCard(jobCardName.value)
		await refreshJobCard()
	} catch (error) {
		const message = (error as Error)?.message || 'Unknown error'
		actionError.value = message
		toast.error(message)
	} finally {
		isBusy.value = false
	}
}

const pauseOperation = async () => {
	if (!jobCardName.value || isBusy.value || !isRunning.value || isCompleted.value) return

	isBusy.value = true
	actionError.value = ''
	try {
		await store.pauseJobCard(jobCardName.value)
		await refreshJobCard()
	} catch (error) {
		const message = (error as Error)?.message || 'Unknown error'
		actionError.value = message
		toast.error(message)
	} finally {
		isBusy.value = false
	}
}

const finishOperation = async () => {
	if (!jobCardName.value || isBusy.value || isCompleted.value) return

	const remainingQty = Math.max(
		0,
		Number(jobCard.value.for_quantity || 0) - Number(jobCard.value.total_completed_qty || 0),
	)
	const defaultQty = remainingQty > 0 ? String(remainingQty) : '1'
	const input = window.prompt('Completed quantity', defaultQty)
	if (input === null) return

	const completedQty = Number(input)
	if (!Number.isFinite(completedQty) || completedQty <= 0) {
		actionError.value = 'Unknown error'
		toast.error('Unknown error')
		return
	}

	isBusy.value = true
	actionError.value = ''
	try {
		await store.finishJobCard(jobCardName.value, completedQty)
		await refreshJobCard()
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
