<template>
	<div class="control-buttons">
		<button @click="onCreate" :disabled="docstatus !== -1">Save</button>
		<button @click="onSubmit" :disabled="docstatus !== 0">Submit</button>
		<button @click="onCancel" :disabled="docstatus !== 1">Cancel</button>
	</div>
</template>

<script setup lang="ts">
import { defineProps, ref } from 'vue'
const docstatus = ref(-1)

const props = defineProps<{
	onCreate: () => Promise<{ data: any }>
	onSubmit: () => Promise<{ data: any; exception: string; response: Response }>
	onCancel: () => Promise<{ data: any; exception: string; response: Response }>
}>()

const onCreate = async () => {
	try {
		const { data } = await props.onCreate()
		if (data) {
			docstatus.value = data.docstatus
		}
	} catch (err) {
		console.error(err)
	}
}

const onSubmit = async () => {
	try {
		const { data } = await props.onSubmit()
		if (data) {
			docstatus.value = data.docstatus
		}
	} catch (err) {
		console.error(err)
	}
}

const onCancel = async () => {
	try {
		const { data } = await props.onCancel()
		if (data) {
			docstatus.value = -1
		}
	} catch (err) {
		console.error(err)
	}
}


</script>

<style scoped>
.control-buttons {
	display: flex;
	justify-content: flex-end;
	gap: 1rem;
}
</style>
