<!-- ControlButtons.vue -->
<template>
	<div class="control-buttons">
		<button @click="onCreate" :disabled="!!docstatus">Save</button>
		<button @click="onSubmit" :disabled="!docstatus">Submit</button>
		<button @click="onCancel" :disabled="!docstatus">Cancel</button>
	</div>
</template>

<script setup lang="ts">
import { defineProps } from 'vue'

const props = defineProps<{
	docstatus: number
	onCreate: () => Promise<void>
	onSubmit: () => Promise<void>
	onCancel: () => Promise<void>
}>()
</script>

<style scoped>
.control-buttons {
	display: flex;
	justify-content: flex-end;
	gap: 1rem;
}
</style>
