<template>
	<div class="control-buttons">
		<button class="btn" @click="onAmend" v-if="docstatus === 2">Amend</button>
		<template v-else>
			<button class="btn" @click="onSave" :disabled="!(docstatus === 0 && doctypeName === '')">Save</button>
			<button class="btn" @click="onSubmit" :disabled="!(docstatus === 0 && doctypeName !== '')">Submit</button>
			<button class="btn" @click="onCancel" :disabled="docstatus !== 1">Cancel</button>
		</template>
	</div>
</template>

<script setup lang="ts" generic="T extends ParentDoctype">
import { ref } from 'vue'

import type { DocActionResponse, ParentDoctype } from '@/types'

const props = defineProps<{
	onCreate: () => Promise<DocActionResponse<T>>
	onSubmit: () => Promise<DocActionResponse<T>>
	onCancel: () => Promise<DocActionResponse<T>>
}>()

const docstatus = ref(0)
const doctypeName = ref('')

const onSave = async () => {
	try {
		const { data } = await props.onCreate()
		if (data) {
			doctypeName.value = data.name
			docstatus.value = data.docstatus
		}
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
	doctypeName.value = ''
}
</script>

<style scoped>
.control-buttons {
	display: flex;
	justify-content: flex-end;
	gap: 1rem;
}
</style>
