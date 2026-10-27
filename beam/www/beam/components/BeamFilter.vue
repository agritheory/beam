<template>
	<div class="beam_filters">
		<div class="beam_filters-heading" @click="isFilterExpanded = !isFilterExpanded">
			<ToggleArrow :open="isFilterExpanded" />
			<BeamHeading>Filter</BeamHeading>
		</div>

		<div v-show="isFilterExpanded" class="beam_filters-options">
			<slot />
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref } from 'vue'

defineSlots<{ default(): any }>()

const isFilterExpanded = ref(false)
</script>

<style scoped>
.beam_filters {
	background-color: var(--sc-primary-color);
	border-bottom: 1px solid var(--sc-row-border-color);
	box-sizing: border-box;
	min-height: 2em;
	overflow: visible;
	padding: 0.625rem;
	transition: all 0.2s ease-in-out;
}

.beam_filters-heading {
	align-items: center;
	background-color: var(--sc-primary-color);
	box-sizing: border-box;
	cursor: pointer;
	display: flex;
	font-size: 1rem;

	& > h1 {
		font-size: 1rem;
	}
}

.beam_filters-options {
	display: flex;
	flex-direction: row;
	justify-content: flex-start;
	margin: 1rem 0;
	padding: 0 1rem;
	gap: 1rem;

	@media (max-width: 479px) {
		flex-direction: column;
	}
}
</style>
