<template>
	<div class="beam_modal-confirm">
		<h2>Would you like to continue?</h2>
		<BeamBtn @click="$emit('confirmmodal')">Yes</BeamBtn>
		<BeamBtn @click="$emit('closemodal')">No</BeamBtn>
	</div>
</template>

<script setup lang="ts">
defineEmits<{ confirmmodal: []; closemodal: [] }>()
</script>

<style scoped>
.beam_modal-confirm {
	background: #ffffff;
	padding: 1.25rem;
	width: 80%;
	max-width: 400px;
	position: absolute;
	top: 50%;
	left: 50%;
	transform: translate(-50%, -50%);

	& button {
		margin: 0.625rem;
	}
	& h2 {
		border-bottom: 1px solid var(--sc-row-border-color);
		padding-bottom: 0.625rem;
		color: var(--sc-primary-text-color);
	}
}
</style>
