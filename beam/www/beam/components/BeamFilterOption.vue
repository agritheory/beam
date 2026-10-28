<template>
	<div v-on-click-outside="() => (isMenuOpen = false)" class="beam_filter-container">
		<BeamHeading class="beam_filter-option-heading">{{ title }}</BeamHeading>
		<div class="beam_filter-option" @click="isMenuOpen = !isMenuOpen">
			<div class="beam_filter-option-select">
				<div class="beam_filter-arrow">
					<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 35.36 70.71">
						<polygon points="0 70.71 0 0 35.36 35.36 0 70.71" />
					</svg>
				</div>
				<div class="beam_filter-label">
					<label>{{ label }}</label>
				</div>
			</div>

			<ul v-if="isMenuOpen" ref="menu" class="beam_filter-select-menu">
				<li
					v-for="choice in choices"
					:key="choice.value"
					:class="{ selected: label == choice.label }"
					:data-value="choice.value"
					class="beam_filter-select-option"
					@click="selectChoice(choice)">
					{{ choice.label }}
				</li>
			</ul>
		</div>
	</div>
</template>

<script setup lang="ts">
import { vOnClickOutside } from '@vueuse/components'
import { ref } from 'vue'

import type { BeamFilterChoice } from '@/types/stonecrop.js'

const emit = defineEmits<{ select: [choice: BeamFilterChoice] }>()

const { choices, title = 'title' } = defineProps<{
	choices: BeamFilterChoice[]
	title?: string
}>()

const isMenuOpen = ref(false)
const label = ref(choices[0].label)
const value = ref(choices[0].value)

const selectChoice = (data: BeamFilterChoice) => {
	label.value = data.label
	value.value = data.value
	emit('select', data)
}
</script>

<style scoped>
.beam_filter-option {
	cursor: pointer;
	position: relative;
}

.beam_filter-option-heading {
	font-size: 1rem !important;
	padding-bottom: 0.25rem;
}

.beam_filter-option-select {
	align-items: stretch;
	appearance: none;
	background-color: white;
	border: 1px solid var(--sc-row-border-color);
	color: var(--sc-primary-text-color);
	display: flex;
	font-family: var(--sc-font-family);
	font-size: 0.8rem;
	font-weight: bold;
	position: relative;
}

label {
	cursor: pointer;
	padding: 0.5rem;
}

.beam_filter-arrow {
	background: var(--sc-primary-color);
	color: var(--sc-primary-text-color);
	cursor: pointer;
	display: flex;
	align-items: center;
	width: 5px;
	padding: 0.5rem 0.7rem;
}

.beam_filter-label {
	display: flex;
	align-items: center;
}

svg {
	fill: var(--sc-primary-text-color);
	width: 5px;
	transform: rotate(90deg);
}

.beam_filter-select-menu {
	background-color: white;
	border-top: none;
	border: 1px solid var(--sc-row-border-color);
	box-sizing: border-box;
	left: 0;
	list-style: none;
	margin: 0;
	max-height: 200px;
	overflow-y: scroll;
	padding: 0rem;
	position: absolute;
	width: 100%;
	z-index: 100;
}

.beam_filter-select-option {
	font-size: 0.8rem;
	font-family: var(--sc-font-family);
	font-weight: bold;
	color: var(--sc-primary-text-color);
	border-bottom: 1px solid var(--sc-row-border-color);
	padding: 0.5rem;
	&:hover {
		background: var(--sc-primary-color);
	}
}

.selected {
	background: var(--sc-row-border-color);

	&:hover {
		background: var(--sc-row-border-color);
	}
}
.beam_filter-container {
	flex-grow: 1;
	max-width: 300px;
	width: 50%;

	@media (max-width: 479px) {
		width: 100%;
		max-width: 100%;
	}
}
</style>
