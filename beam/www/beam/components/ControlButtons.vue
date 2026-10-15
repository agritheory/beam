<template>
	<div class="control-buttons-footer">
		<Teleport to="body">
			<div v-if="busy" class="control-buttons-busy-overlay" aria-busy="true" />
		</Teleport>
		<div class="control-buttons-spacer" aria-hidden="true" />
		<div class="control-buttons">
			<BeamBtn
				v-for="(button, index) in buttons"
				v-show="!button.hidden"
				:key="index"
				:class="{ 'footer-full-row': index === fullWidthIndex }"
				@click="event => runAction(event, button)"
				:disabled="isDisabled(button)"
				:style="{
					'background-color': !isDisabled(button) ? button.color?.background || 'inherit' : 'inherit',
					color: !isDisabled(button) ? button.color?.text || 'inherit' : 'inherit',
					cursor: !isDisabled(button) ? 'auto' : 'not-allowed',
				}">
				{{ button.label }}
			</BeamBtn>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, onUnmounted, ref, watch } from 'vue'

import type { ControlButton } from '@/types'

const props = defineProps<{ buttons: ControlButton[] }>()

const busy = ref(false)

const visibleIndexes = computed(() => props.buttons.flatMap((button, index) => (button.hidden ? [] : [index])))

// Buttons pair up two per row; an odd one out spans the row so the grid has no gap.
const fullWidthIndex = computed(() => {
	const visible = visibleIndexes.value
	return visible.length % 2 === 1 ? visible[visible.length - 1] : -1
})

const footerRows = computed(() => Math.max(1, Math.ceil(visibleIndexes.value.length / 2)))

const isDisabled = (button: ControlButton) => busy.value || Boolean(button.disabled)

const runAction = async (event: MouseEvent, button: ControlButton) => {
	if (isDisabled(button) || !button.action) {
		return
	}

	busy.value = true

	try {
		const result = button.action(event)
		await Promise.resolve(result)
	} finally {
		busy.value = false
	}
}

// Camera's FAB sits above the footer, outside this component, so the row count lives on :root.
const setFooterRows = (rows: number) => document.documentElement.style.setProperty('--beam-footer-rows', String(rows))

watch(footerRows, setFooterRows, { immediate: true })

onUnmounted(() => setFooterRows(1))
</script>

<style scoped>
.control-buttons-busy-overlay {
	position: fixed;
	inset: 0;
	z-index: 160; /* above camera FAB (150), below camera modal (250) */
	pointer-events: all;
}

.control-buttons-spacer {
	height: var(--beam-footer-height);
}

.control-buttons {
	display: flex;
	flex-wrap: wrap-reverse;
	flex-direction: row-reverse;
	gap: 0.5rem;
	box-sizing: border-box;
	width: 100%;
	max-width: 100%;
	padding: 0.5rem;
	padding-bottom: calc(0.5rem + env(safe-area-inset-bottom, 0px));
	position: fixed;
	left: 0;
	right: 0;
	bottom: 0;
	justify-content: space-between;
	background: var(--sc-btn-color);
	border-top: 1px solid var(--sc-row-border-color);
	z-index: 100;
}

.control-buttons > button {
	flex: 1 1 0;
	min-width: 0;
	max-width: calc(50% - 0.25rem);
	letter-spacing: 0.05rem;
	font-weight: bold;
	transition: background-color 120ms ease-out;
}

.control-buttons > button:focus-visible {
	outline: 2px solid var(--sc-focus-cell-outline);
	outline-offset: 2px;
}

.control-buttons > button.footer-full-row {
	flex: 1 1 100%;
	max-width: 100%;
}
</style>
