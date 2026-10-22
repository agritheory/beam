<template>
	<nav class="beam_navbar">
		<slot name="title">
			<BeamHeading>TITLE</BeamHeading>
		</slot>
		<BeamBtn @click="handlePrimaryAction">
			<slot name="navbaraction">Action</slot>
		</BeamBtn>
	</nav>
</template>

<script setup lang="ts">
const emit = defineEmits<{ click: [] }>()

const handlePrimaryAction = () => {
	emit('click')
}
</script>

<style scoped>
.beam_navbar {
	padding: 0.625rem;
	background-color: var(--sc-primary-color);
	margin-left: 0;
	min-height: 2em;
	max-height: 2em;
	color: var(--sc-primary-text-color);
	display: flex;
	flex-flow: row nowrap;
	align-content: center;
	justify-content: space-between;
	align-items: center;
	position: sticky;
	top: 0;
	font-family: var(--sc-font-family);
	border-bottom: 1px solid var(--sc-row-border-color);

	& h1 {
		margin-left: 0.625rem;
	}
}
</style>
