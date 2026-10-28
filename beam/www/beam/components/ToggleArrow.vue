<template>
	<div class="arrow-icon" :class="{ open }">
		<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 35.36 70.71">
			<polygon points="0 70.71 0 0 35.36 35.36 0 70.71" />
		</svg>
	</div>
</template>

<script setup lang="ts">
const { open } = defineProps<{ open: boolean }>()
</script>

<style scoped>
svg {
	width: 100%;
	overflow: visible;
	fill: var(--sc-primary-text-color);
}

.arrow-icon {
	width: 0.4rem;
	transform: rotate(0);
	transform-origin: center;
	position: relative;
	transition: all 0.1s ease-in-out;
	margin: 0.5rem;
	cursor: pointer;
	display: flex;
	align-items: center;
}

.open {
	transform: rotate(90deg);
}
</style>
