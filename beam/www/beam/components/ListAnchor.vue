<template>
	<a :href="to" class="beam_list-anchor">
		<slot />
	</a>
</template>

<script setup lang="ts">
const { to = '' } = defineProps<{ to?: string }>()
</script>

<style scoped>
.beam_list-anchor {
	text-decoration: none;
	outline: none;
	color: var(--sc-primary-text-color);
}
</style>
