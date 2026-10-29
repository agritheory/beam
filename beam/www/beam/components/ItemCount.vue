<template>
	<div class="beam_item-count">
		<span
			ref="countEl"
			:contenteditable="editable"
			inputmode="decimal"
			:class="{ 'beam--alert': !isCountComplete }"
			@click.stop.prevent="validate"
			@input.stop.prevent="debouncedValidate"
			@paste="validate"
			@beforeinput="preventLineBreak"
			@keydown="detectScan"
			@keydown.enter="blurOnEnter"
			@blur="onBlur"></span>
		<span v-if="denominator">/{{ denominator }}</span>
		<span v-if="uom">&nbsp; {{ uom }}</span>
	</div>
</template>

<script setup lang="ts">
import { useDebounceFn } from '@vueuse/core'
import { computed, onMounted, ref, watch, type HTMLAttributes } from 'vue'

const countEl = ref<HTMLElement | null>(null)
const count = defineModel<number>({ required: true })
const {
	denominator = 0,
	debounce = 300,
	editable = true,
	uom = '',
} = defineProps<{
	denominator?: number
	debounce?: number
	editable?: HTMLAttributes['contenteditable']
	uom?: string
}>()

const isCountComplete = computed(() => denominator !== 0 && count.value === denominator)

const validate = (payload: ClipboardEvent | InputEvent | MouseEvent | FocusEvent) => {
	const newValue = Number((payload.target as HTMLElement).textContent) || 0
	count.value = denominator ? Math.min(newValue, denominator) : newValue
}

const onBlur = (payload: FocusEvent) => {
	validate(payload)
	render()
}

const preventLineBreak = (payload: InputEvent) => {
	if (payload.inputType === 'insertParagraph' || payload.inputType === 'insertLineBreak') payload.preventDefault()
}
const SCAN_MIN_LENGTH = 6
const SCAN_MS_PER_CHAR = 30
const SCAN_GAP_MS = 100
let burst = { baseline: '', start: 0, last: 0, length: 0 }

const detectScan = (payload: KeyboardEvent) => {
	if (payload.key.length !== 1 || payload.ctrlKey || payload.metaKey) return
	const el = payload.target as HTMLElement
	if (payload.timeStamp - burst.last > SCAN_GAP_MS) {
		burst = { baseline: el.textContent ?? '', start: payload.timeStamp, last: payload.timeStamp, length: 1 }
		return
	}
	burst.last = payload.timeStamp
	burst.length++
	if (burst.length < SCAN_MIN_LENGTH || burst.last - burst.start > burst.length * SCAN_MS_PER_CHAR) return
	el.textContent = burst.baseline
	burst = { baseline: '', start: 0, last: 0, length: 0 }
	el.blur()
}

const blurOnEnter = (payload: KeyboardEvent) => (payload.target as HTMLElement).blur()

const selectContents = (el: HTMLElement, collapseToEnd = false) => {
	const selection = window.getSelection()
	if (!selection) return
	const range = document.createRange()
	range.selectNodeContents(el)
	if (collapseToEnd) range.collapse(false)
	selection.removeAllRanges()
	selection.addRange(range)
}

const render = () => {
	if (countEl.value) countEl.value.textContent = String(count.value ?? '')
}

const sync = () => {
	const el = countEl.value
	if (!el) return
	if (document.activeElement !== el) return render()
	if ((Number(el.textContent) || 0) === count.value) return
	render()
	selectContents(el, true)
}

onMounted(render)
watch(count, sync)

const focus = () => {
	const el = countEl.value
	if (!el) return
	el.focus()
	selectContents(el)
}

defineExpose({ focus })

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
