<template>
	<div class="inspection-line">
		<div class="inspection-line-body">
			<slot />
		</div>
		<component
			:is="to ? 'RouterLink' : 'span'"
			v-bind="to ? { to } : {}"
			class="inspection-icon"
			:class="`inspection-icon--${iconKind}`"
			:aria-label="ariaLabel"
			:title="ariaLabel"
			@click.stop>
			<svg class="inspection-icon-svg" viewBox="0 0 24 24" aria-hidden="true">
				<path
					v-if="iconKind === 'needed'"
					fill="currentColor"
					d="M19 3h-4.18C14.4 1.84 13.3 1 12 1s-2.4.84-2.82 2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-7 0c.55 0 1 .45 1 1s-.45 1-1 1-1-.45-1-1 .45-1 1-1zm2 14H8v-2h6v2zm0-4H8v-2h6v2zm0-4H8V7h6v2z" />
				<path
					v-else-if="iconKind === 'draft'"
					fill="currentColor"
					d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H8v-2h6v2zm0-4H8v-2h6v2zm-7-4V7h6v2H7z" />
				<path
					v-else-if="iconKind === 'Accepted'"
					fill="currentColor"
					d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />
				<path
					v-else-if="iconKind === 'Rejected'"
					fill="currentColor"
					d="M12 2C6.47 2 2 6.47 2 12s4.47 10 10 10 10-4.47 10-10S17.53 2 12 2zm5 13.59L15.59 17 12 13.41 8.41 17 7 15.59 10.59 12 7 8.41 8.41 7 12 10.59 15.59 7 17 8.41 13.41 12 17 15.59z" />
				<path
					v-else
					fill="currentColor"
					d="M19 3h-4.18C14.4 1.84 13.3 1 12 1s-2.4.84-2.82 2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-7 0c.55 0 1 .45 1 1s-.45 1-1 1-1-.45-1-1 .45-1 1-1zm2 14H8v-2h6v2zm0-4H8v-2h6v2zm0-4H8V7h6v2z" />
			</svg>
		</component>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import { inspectionAriaLabel } from '@/utils/inspectionList'

const props = defineProps<{
	to?: string
	state?: string
}>()

const iconKind = computed(() => {
	if (props.state) return props.state
	if (!props.to) return 'needed'
	const queryPart = props.to.includes('?') ? props.to.split('?')[1] : ''
	if (!queryPart) return 'needed'
	const parsed = new URLSearchParams(queryPart).get('state')
	return parsed || 'needed'
})

const ariaLabel = computed(() => inspectionAriaLabel(iconKind.value))
</script>

<style scoped>
.inspection-line {
	display: flex;
	align-items: stretch;
	width: 100%;
}

.inspection-line-body {
	flex: 1;
	min-width: 0;
}

.inspection-icon {
	display: flex;
	align-items: center;
	justify-content: center;
	padding: 0 0.75rem;
	color: var(--sc-cell-text-color);
	flex-shrink: 0;
}

.inspection-icon:focus-visible {
	outline: 2px solid var(--sc-focus-cell-outline);
	outline-offset: 2px;
}

.inspection-icon-svg {
	width: 1.5rem;
	height: 1.5rem;
}

.inspection-icon--needed {
	color: var(--sc-beam-warning-text, #6b4a00);
}

.inspection-icon--Rejected {
	color: var(--sc-beam-danger-fill);
}

.inspection-icon--Accepted {
	color: var(--sc-success, #2e7d32);
}

.inspection-icon:has(+ *) {
	/* keep spacing */
}
</style>
