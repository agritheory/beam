<template>
	<div
		class="control-buttons-footer"
		:class="{ 'has-full-row': showsFullWidthRow }"
		:style="{ '--beam-footer-rows': showsFullWidthRow ? 2 : 1 }">
		<div class="control-buttons-spacer" aria-hidden="true" />
		<div class="control-buttons">
			<BeamBtn
				v-for="(button, index) in buttons"
				v-show="!button.hidden"
				:key="index"
				:class="{ 'footer-full-row': isFullWidthSlot(index) }"
				@click="button.action"
				:disabled="button.disabled"
				:style="{
					'background-color': !button.disabled ? button.color?.background || 'inherit' : 'inherit',
					color: !button.disabled ? button.color?.text || 'inherit' : 'inherit',
					cursor: !button.disabled ? 'auto' : 'not-allowed',
				}">
				{{ button.label }}
			</BeamBtn>
		</div>
	</div>
</template>

<script setup lang="ts">
import { computed, onUnmounted, watch } from 'vue'

import type { ControlButton } from '@/types'

const props = defineProps<{ buttons: ControlButton[] }>()

const visibleCount = computed(() => props.buttons.filter(button => !button.hidden).length)

const showsFullWidthRow = computed(() => {
	const last = props.buttons[props.buttons.length - 1]
	return Boolean(last && !last.hidden && visibleCount.value > 1)
})

function isFullWidthSlot(index: number): boolean {
	const lastIndex = props.buttons.length - 1
	if (index !== lastIndex) return false
	return !props.buttons[lastIndex]?.hidden
}

function syncFooterCssVars(rows: number) {
	const root = document.documentElement
	root.style.setProperty('--beam-footer-rows', String(rows))
	root.style.removeProperty('--beam-footer-height')
}

watch(showsFullWidthRow, hasFullRow => syncFooterCssVars(hasFullRow ? 2 : 1), { immediate: true })

onUnmounted(() => syncFooterCssVars(1))
</script>

<style scoped>
.control-buttons-spacer {
	height: calc(var(--beam-footer-rows, 1) * 3.25rem + 1rem + env(safe-area-inset-bottom, 0px));
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
	background: var(--sc-background-color, #fff);
	border-top: 1px solid var(--sc-row-border-color, #ccc);
	z-index: 100;
}

.control-buttons > button {
	flex: 1 1 0;
	min-width: 0;
	max-width: calc(50% - 0.25rem);
	letter-spacing: 0.05rem;
	font-weight: bold;
}

.control-buttons > button.footer-full-row {
	flex: 1 1 100%;
	max-width: 100%;
}
</style>

<style>
/* Shared with Camera FAB — updated when footer uses two rows (visible full-width slot). */
.control-buttons-footer {
	--beam-footer-rows: 1;
	--beam-footer-height: calc(var(--beam-footer-rows) * 3.25rem + 1rem + env(safe-area-inset-bottom, 0px));
}

.control-buttons-footer.has-full-row {
	--beam-footer-rows: 2;
}
</style>
