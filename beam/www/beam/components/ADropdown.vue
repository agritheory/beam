<template>
	<div class="aform_form-element">
		<template v-if="mode === 'display'">
			<span class="aform_display-value">{{ search }}</span>
			<label class="aform_field-label">{{ label }}</label>
		</template>
		<template v-else>
			<div v-on-click-outside="onClickOutside" class="autocomplete" :class="{ isOpen: dropdown.open }">
				<input
					:id="uuid"
					ref="inputRef"
					v-model="search"
					type="text"
					role="combobox"
					autocomplete="off"
					aria-autocomplete="list"
					class="aform_input-field"
					:disabled="mode === 'read'"
					:required="required"
					:aria-expanded="dropdown.open"
					:aria-controls="dropdown.open ? listboxId : undefined"
					:aria-activedescendant="
						dropdown.activeItemIndex === null ? undefined : `${listboxId}-opt-${dropdown.activeItemIndex}`
					"
					:aria-invalid="invalid"
					:aria-describedby="describedBy"
					@input="onComboboxInput"
					@focus="openDropdown"
					@keydown.down.prevent="selectNextResult"
					@keydown.up.prevent="selectPrevResult"
					@keydown.enter.prevent="setCurrentResult"
					@keydown.esc="onClickOutside"
					@keydown.tab="onClickOutside" />

				<ul
					v-show="dropdown.open"
					:id="listboxId"
					ref="resultsRef"
					class="autocomplete-results"
					role="listbox"
					:aria-label="label ?? ''">
					<li v-if="dropdown.loading" class="loading autocomplete-result">Loading results...</li>
					<li
						v-for="(result, i) in dropdown.results"
						v-else
						:id="`${listboxId}-opt-${i}`"
						:key="result"
						role="option"
						:aria-selected="isChoiceSelected(result)"
						class="autocomplete-result"
						:class="{ 'is-active': i === dropdown.activeItemIndex, 'is-selected': isChoiceSelected(result) }"
						@mousedown.prevent="setChoiceResult(result)"
						@mouseenter="dropdown.activeItemIndex = i">
						{{ result }}
					</li>
					<li
						v-if="showHint"
						role="presentation"
						class="autocomplete-hint"
						@mousedown.prevent="dismissHint">
						{{ hint }}
					</li>
					<li v-if="showEmptyText" role="presentation" class="autocomplete-empty" @mousedown.prevent>
						{{ emptyText }}
					</li>
				</ul>
				<label class="aform_field-label" :for="uuid">{{ label }}</label>
			</div>
			<p v-show="errorText" :id="errorId" class="aform_error" role="alert">{{ errorText }}</p>
		</template>
	</div>
</template>

<script setup lang="ts">
import { vOnClickOutside } from '@vueuse/components'
import { computed, reactive, ref, useId, useTemplateRef, watch } from 'vue'

import { fitDropdownList } from '@/composables/dropdownList'
import { fieldErrorA11y } from '@/composables/fieldErrorA11y'

const {
	label,
	required,
	options = [],
	isAsync = false,
	filterFunction = undefined,
	hint = '',
	emptyText = '',
	mode,
	uuid,
	errors,
	validation = { errorMessage: '' },
} = defineProps<{
	label?: string
	required?: boolean
	options?: string[]
	isAsync?: boolean
	filterFunction?: (search: string) => string[] | Promise<string[]>
	hint?: string
	emptyText?: string
	mode?: 'edit' | 'read' | 'display'
	uuid?: string
	errors?: string[]
	validation?: { errorMessage: string }
}>()

const listboxId = `${uuid ?? `aform-dropdown-${useId()}`}-listbox`

const choiceList = computed(() => options)

const errorText = computed(() => (errors?.length ? errors.join('; ') : validation.errorMessage ?? ''))
const { errorId, describedBy, invalid } = fieldErrorA11y(uuid, errorText)

const modelValue = defineModel<string>()

const dropdown = reactive({
	activeItemIndex: null as number | null,
	open: false,
	loading: false,
	searched: false,
	results: [] as string[],
})

const resultsRef = useTemplateRef<HTMLElement>('resultsRef')
const inputRef = useTemplateRef<HTMLInputElement>('inputRef')

const noResults = computed(() => !dropdown.loading && dropdown.results.length === 0)
const showHint = computed(() => !!hint && noResults.value && (!dropdown.searched || !search.value))
const showEmptyText = computed(() => !!emptyText && noResults.value && dropdown.searched && !!search.value)

fitDropdownList(resultsRef, {
	isOpen: () => dropdown.open,
	optionCount: () => dropdown.results.length,
	activeIndex: () => dropdown.activeItemIndex,
})

const committedValue = ref(modelValue.value ?? '')

const search = ref('')

// Keeps `search`/`committedValue` in sync with the model however it changes — including an
// external clear (v-model set from outside, e.g. a "clear field" button) — so the next
// outside click doesn't revert the field to a stale committed value.
watch(
	modelValue,
	value => {
		const next = value ?? ''
		search.value = next
		if (next === '' || choiceList.value.includes(next)) committedValue.value = next
	},
	{ immediate: true }
)

const onClickOutside = () => closeDropdown()

const isChoiceSelected = (result: string) => !!result && result === (modelValue.value ?? '')

const filterResults = () => {
	if (!search.value) {
		dropdown.results = choiceList.value
	} else {
		dropdown.results = choiceList.value.filter(item => item.toLowerCase().includes(search.value.toLowerCase()))
	}
}

const filter = async () => {
	dropdown.open = true
	dropdown.activeItemIndex = null
	dropdown.searched = false
	if (filterFunction) {
		if (isAsync) dropdown.loading = true
		try {
			const filteredResults = await filterFunction(search.value || '')
			dropdown.results = filteredResults || []
		} catch {
			dropdown.results = []
		} finally {
			if (isAsync) dropdown.loading = false
			dropdown.searched = true
		}
	} else {
		filterResults()
	}
}

const onComboboxInput = () => {
	modelValue.value = search.value
	filter()
}

const setChoiceResult = (result: string) => {
	modelValue.value = result
	search.value = result
	committedValue.value = result
	closeDropdown(result)
}

const openDropdown = () => {
	const idx = choiceList.value.indexOf(search.value)
	dropdown.activeItemIndex = isAsync ? null : idx >= 0 ? idx : null
	dropdown.open = true
	dropdown.searched = false
	dropdown.results = isAsync ? [] : choiceList.value
}

const closeDropdown = (result?: string) => {
	dropdown.activeItemIndex = null
	dropdown.open = false
	const typed = result || search.value || ''
	if (choiceList.value.includes(typed)) {
		if (typed !== committedValue.value) {
			modelValue.value = typed
			committedValue.value = typed
		}
	} else {
		search.value = committedValue.value
		modelValue.value = committedValue.value
	}
}

const dismissHint = () => {
	closeDropdown()
	inputRef.value?.blur()
}

const selectNextResult = () => {
	const resultsLength = dropdown.results.length
	if (!resultsLength) return
	if (!dropdown.open) {
		openDropdown()
		if (dropdown.activeItemIndex === null && !isAsync) dropdown.activeItemIndex = 0
		return
	}
	if (dropdown.activeItemIndex != null) {
		dropdown.activeItemIndex = (dropdown.activeItemIndex + 1) % resultsLength
	} else {
		dropdown.activeItemIndex = 0
	}
}

const selectPrevResult = () => {
	const resultsLength = dropdown.results.length
	if (!resultsLength) return
	if (!dropdown.open) openDropdown()
	if (dropdown.activeItemIndex != null) {
		if (dropdown.activeItemIndex === 0) {
			dropdown.activeItemIndex = null
		} else {
			dropdown.activeItemIndex = dropdown.activeItemIndex - 1
		}
	} else {
		dropdown.activeItemIndex = resultsLength - 1
	}
}

const setCurrentResult = () => {
	if (!dropdown.open) {
		openDropdown()
		return
	}
	const result = dropdown.results[dropdown.activeItemIndex ?? 0]
	if (result !== undefined) setChoiceResult(result)
}

watch(
	choiceList,
	choices => {
		dropdown.results = choices
	},
	{ immediate: true }
)
</script>

<style scoped>
.autocomplete {
	position: relative;
}

.autocomplete-results {
	position: absolute;
	top: 100%;
	left: 0;
	right: 0;
	z-index: 100;
	box-sizing: border-box;
	padding: 0;
	margin: 0;
	color: var(--sc-cell-text-color);
	border: 1px solid var(--sc-row-border-color);
	border-radius: 0 0 var(--sc-border-radius) var(--sc-border-radius);
	border-top: none;
	background-color: var(--sc-overlay-background);
	box-shadow: var(--sc-overlay-shadow);
	list-style: none;
	max-height: var(--sc-dropdown-max-height);
	overflow-y: auto;
}

.autocomplete-results:empty {
	display: none;
}

.autocomplete-result {
	text-align: left;
	box-sizing: border-box;
	border-left: 2px solid transparent;
	padding: 0.35rem 0.75ch 0.35rem 0.25ch;
	cursor: pointer;
	color: var(--sc-cell-text-color);
}

.autocomplete-result:hover,
.autocomplete-result.is-active {
	background-color: var(--sc-dropdown-option-hover-background);
	color: var(--sc-cell-text-color);
}

.autocomplete-hint,
.autocomplete-empty {
	text-align: left;
	box-sizing: border-box;
	border-left: 2px solid transparent;
	padding: 0.35rem 0.75ch 0.35rem 0.25ch;
	color: var(--sc-input-label-color);
}

.autocomplete-result.is-selected {
	border-left-color: var(--sc-dropdown-option-selected-accent);
}
</style>
