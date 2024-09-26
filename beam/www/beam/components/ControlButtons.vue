<template>
	<div class="control-buttons">
		<button class="btn" @click="onCreate" :disabled="docstatus !== -1">Save</button>
		<button class="btn" @click="onSubmit" :disabled="docstatus !== 0">Submit</button>
		<button class="btn" @click="onCancel" :disabled="docstatus !== 1">Cancel</button>
	</div>
</template>

<script setup lang="ts" generic="T extends ParentDoctype">
import { ParentDoctype } from '@/types';
import { defineProps, ref } from 'vue'
const docstatus = ref(-1)

const props = defineProps<{
	onCreate: () => Promise<{ data: T }>
	onSubmit: () => Promise<{ data: T; exception: string; response: Response }>
	onCancel: () => Promise<{ data: T; exception: string; response: Response }>
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
