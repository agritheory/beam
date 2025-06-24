<template>
	<div class="beam_item-count">
		<span
			:contenteditable="editable"
			:class="{ 'beam--alert': !isCountComplete }"
			@click.stop.prevent="validate"
			@input.stop.prevent="debouncedValidate"
			@paste="validate">
			{{ count }}
		</span>
		<span v-if="denominator">/{{ denominator }}</span>
		<span v-if="uom">&nbsp; {{ uom }}</span>
	</div>
</template>

<script setup lang="ts">
import { useDebounceFn } from '@vueuse/core'
import { computed, type HTMLAttributes } from 'vue'

const count = defineModel<number>({ required: true })
const {
	denominator = 0,
	debounce = 300,
	editable = true,
	uom = '',
} = defineProps<{
	denominator: number
	debounce?: number
	editable?: HTMLAttributes['contenteditable']
	uom?: string
}>()

const isCountComplete = computed(() => denominator !== 0 && count.value === denominator)

const validate = (payload: ClipboardEvent | InputEvent | MouseEvent) => {
	const newValue = Number((payload.target as HTMLElement).innerHTML) || 0
	count.value = denominator ? Math.min(newValue, denominator) : newValue
}

const debouncedRequest = useDebounceFn((payload: InputEvent) => validate(payload), debounce)
const debouncedValidate = async (payload: InputEvent) => await debouncedRequest(payload)
</script>

<style scoped>
.beam_item-count {
	font-size: 1.3125rem;
	color: var(--sc-primary-text-color);
}

.beam_item-count span {
	margin: 0;
	padding: 0;
	outline: none;
}
</style>
