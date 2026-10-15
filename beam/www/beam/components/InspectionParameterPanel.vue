<template>
	<section class="inspection-parameter" :data-inspection-parameter="reading.parameter">
		<button type="button" class="inspection-parameter-header" @click="emit('toggle')">
			<div class="inspection-parameter-heading">
				<span class="beam--bold">{{ reading.label }}</span>
				<p v-if="reading.hint" class="inspection-parameter-hint">{{ reading.hint }}</p>
				<p class="inspection-parameter-summary">{{ summary }}</p>
			</div>
			<ToggleArrow :open="expanded" />
		</button>

		<div v-show="expanded" class="inspection-parameter-body">
			<template v-if="reading.kind === 'passfail'">
				<div class="passfail">
					<BeamBtn
						type="button"
						class="passfail-btn"
						:disabled="!editable"
						:class="{ 'passfail-btn--active passfail-btn--accept': reading.values[0] === 'Accepted' }"
						@click="emit('answer', ['Accepted'])">
						Accept
					</BeamBtn>
					<BeamBtn
						type="button"
						class="passfail-btn"
						:disabled="!editable"
						:class="{ 'passfail-btn--active passfail-btn--reject': reading.values[0] === 'Rejected' }"
						@click="emit('answer', ['Rejected'])">
						Reject
					</BeamBtn>
				</div>
			</template>

			<template v-else-if="reading.kind === 'numeric'">
				<div v-for="idx in slotCount" :key="idx" class="inspection-reading-row">
					<label class="inspection-field-label" :for="fieldId(idx)"> Reading {{ idx }} </label>
					<div class="inspection-reading-input-row">
						<input
							:id="fieldId(idx)"
							class="inspection-field-input"
							type="text"
							inputmode="decimal"
							:disabled="!editable"
							:value="reading.values[idx - 1] || ''"
							@input="onNumeric(idx, ($event.target as HTMLInputElement).value)" />
						<BeamBtn
							v-if="editable && slotCount > 1"
							type="button"
							class="clear-reading-btn"
							:aria-label="`Remove reading ${idx}`"
							@click="emit('remove-reading', idx)">
							X
						</BeamBtn>
					</div>
				</div>
				<p v-if="slotCount >= maxSlots" class="inspection-limit-note">Up to {{ maxSlots }} readings</p>
			</template>

			<template v-else>
				<label class="inspection-field-label" :for="fieldId(1)">{{ reading.label }}</label>
				<input
					:id="fieldId(1)"
					class="inspection-field-input"
					type="text"
					:disabled="!editable"
					:value="reading.values[0] || ''"
					@input="emit('answer', [($event.target as HTMLInputElement).value])" />
			</template>

			<div v-if="editable" class="parameter-actions">
				<BeamBtn
					type="button"
					class="param-action-save"
					:disabled="saving"
					:style="saveButtonStyle"
					@click="emit('save')">
					Save
				</BeamBtn>
				<BeamBtn
					v-if="showAddReading"
					type="button"
					class="param-action-add"
					:disabled="saving"
					@click="emit('add-reading')">
					Add a reading
				</BeamBtn>
			</div>
		</div>
	</section>
</template>

<script setup lang="ts">
import { BeamBtn, ToggleArrow } from '@stonecrop/beam'
import { computed } from 'vue'

import type { InspectionReading } from '@/types/inspection'

const props = withDefaults(
	defineProps<{
		reading: InspectionReading
		editable: boolean
		expanded: boolean
		slotCount: number
		maxSlots?: number
		saving?: boolean
	}>(),
	{ maxSlots: 10, saving: false }
)

const emit = defineEmits<{
	toggle: []
	'add-reading': []
	'remove-reading': [index: number]
	save: []
	answer: [values: string[]]
}>()

const showAddReading = computed(
	() => props.reading.kind === 'numeric' && props.editable && props.slotCount < props.maxSlots
)

const saveButtonStyle = computed(() => ({
	background: 'var(--sc-success)',
	color: 'var(--sc-btn-color)',
	borderColor: 'var(--sc-success)',
}))

const fieldId = (index: number) => `qi-${props.reading.parameter.replace(/\W+/g, '-')}-${index}`

const filledNumericCount = computed(() => props.reading.values.filter(v => String(v ?? '').trim() !== '').length)

const summary = computed(() => {
	if (props.reading.kind === 'passfail') {
		const v = props.reading.values[0]
		if (v === 'Accepted' || v === 'Rejected') return v
		return 'Not set'
	}
	if (props.reading.kind === 'numeric') {
		const filled = filledNumericCount.value
		if (!filled) return `${props.slotCount} reading slot${props.slotCount === 1 ? '' : 's'}`
		return `${filled} of ${props.slotCount} filled`
	}
	const text = props.reading.values[0]
	return text ? String(text) : 'Not set'
})

const onNumeric = (index: number, value: string) => {
	const values = [...props.reading.values]
	while (values.length < props.slotCount) values.push('')
	values[index - 1] = value
	emit('answer', values)
}
</script>

<style scoped>
.inspection-parameter {
	border-bottom: 1px solid var(--sc-row-border-color);
	font-family: var(--sc-font-family);
}

.inspection-parameter-header {
	width: 100%;
	display: flex;
	align-items: flex-start;
	justify-content: space-between;
	gap: 0.75rem;
	padding: 0.75rem var(--sc-list-margin);
	background: var(--sc-btn-color);
	border: none;
	cursor: pointer;
	text-align: left;
	color: var(--sc-primary-text-color);
}

.inspection-parameter-header:focus-visible {
	outline: 2px solid var(--sc-focus-cell-outline);
	outline-offset: -2px;
}

.inspection-parameter-heading {
	flex: 1;
	min-width: 0;
}

.inspection-parameter-heading .beam--bold {
	display: block;
	font-size: 0.9375rem;
	color: var(--sc-primary-text-color);
}

.inspection-parameter-hint {
	margin: 0.25rem 0 0;
	font-size: 0.8125rem;
	color: var(--sc-primary-text-color);
	opacity: 0.85;
}

.inspection-parameter-summary {
	margin: 0.35rem 0 0;
	font-size: 0.8125rem;
	color: var(--sc-primary-text-color);
	opacity: 0.7;
}

.inspection-parameter-body {
	padding: 0 var(--sc-list-margin) 1rem;
	background: var(--sc-btn-color);
}

.inspection-reading-row {
	margin-bottom: 0.75rem;
}

.inspection-reading-input-row {
	display: flex;
	align-items: stretch;
	gap: 0.5rem;
}

.inspection-reading-input-row .inspection-field-input {
	flex: 1;
	min-width: 0;
}

.clear-reading-btn {
	align-self: stretch;
	margin: 0;
	padding: 0 0.75rem;
	min-width: 2.75rem;
	flex-shrink: 0;
}

.inspection-field-label {
	display: block;
	margin-bottom: 0.35rem;
	font-size: 0.8125rem;
	font-weight: 600;
	color: var(--sc-primary-text-color);
}

.inspection-field-input {
	box-sizing: border-box;
	width: 100%;
	font-family: var(--sc-font-family);
	font-size: 1rem;
	font-weight: 600;
	color: var(--sc-primary-text-color);
	background: var(--sc-btn-color);
	border: 1px solid var(--sc-row-border-color);
	padding: 0.5rem 0.625rem;
}

.inspection-field-input:focus-visible {
	outline: 2px solid var(--sc-focus-cell-outline);
	outline-offset: 0;
}

.inspection-field-input:disabled {
	opacity: 0.65;
}

.passfail {
	display: flex;
	flex-wrap: wrap;
	gap: 0.5rem;
}

.passfail-btn--active {
	outline: 2px solid var(--sc-focus-cell-outline);
}

.passfail-btn--accept.passfail-btn--active {
	background: var(--sc-success);
	color: var(--sc-btn-color);
	border-color: var(--sc-success);
}

.passfail-btn--reject.passfail-btn--active {
	background: var(--sc-alert);
	color: var(--sc-btn-color);
	border-color: var(--sc-alert);
}

.parameter-actions {
	display: flex;
	flex-direction: row-reverse;
	flex-wrap: wrap-reverse;
	gap: 0.5rem;
	margin-top: 0.75rem;
}

.parameter-actions > button {
	flex: 1 1 0;
	min-width: 0;
	max-width: calc(50% - 0.25rem);
	letter-spacing: 0.05rem;
	font-weight: bold;
}

.parameter-actions > .param-action-save:only-child {
	max-width: 100%;
}

.inspection-limit-note {
	margin: 0.5rem 0 0;
	font-size: 0.8125rem;
	color: var(--sc-primary-text-color);
	opacity: 0.7;
}
</style>
