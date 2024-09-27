<template>
	<div class="control-buttons">
		<button class="btn" @click="onAmend" v-if="docstatus === 2">Amend</button>
		<template v-else>
			<button class="btn" @click="onSave" :disabled="!(docstatus === 0 && doctypeName === '')">Save</button>
			<button class="btn" @click="onSubmit" :disabled="!(docstatus === 0 && doctypeName !== '')">Submit</button>
			<button class="btn" @click="onCancel" :disabled="!(docstatus === 1)">Cancel</button>
		</template>
	</div>
</template>

<script setup lang="ts" generic="T extends ParentDoctype">
import { ParentDoctype } from '@/types';
import { defineProps, ref } from 'vue'
const docstatus = ref(0)
const doctypeName = ref("")

const props = defineProps<{
	onCreate: () => Promise<{ data: T }>
	onSubmit: () => Promise<{ data: T; exception: string; response: Response }>
	onCancel: () => Promise<{ data: T; exception: string; response: Response }>
}>()

const onSave = async () => {
	try {
		const { data } = await props.onCreate()
		doctypeName.value = data.name
		if (data) docstatus.value = data.docstatus
	} catch (err) {
		console.error(err)
	}
}

const onSubmit = async () => {
	try {
		const { data } = await props.onSubmit()
		if (data) docstatus.value = data.docstatus
	} catch (err) {
		console.error(err)
	}
}

const onCancel = async () => {
	try {
		const { data } = await props.onCancel()
		if (data) docstatus.value = 2
	} catch (err) {
		console.error(err)
	}
}

const onAmend = () => {
	docstatus.value = 0
	doctypeName.value = ""
}

</script>

<style scoped>
.control-buttons {
	display: flex;
	justify-content: flex-end;
	gap: 1rem;
}
</style>
