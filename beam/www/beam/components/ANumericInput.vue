<template>
	<div class="aform_form-element">
		<template v-if="mode === 'display'">
			<span class="aform_display-value">{{ inputNumber ?? '' }}</span>
			<label class="aform_field-label">{{ label }}</label>
		</template>
		<template v-else>
			<input
				:id="uuid"
				v-model="boxNumber"
				class="aform_input-field"
				type="number"
				:disabled="mode === 'read'"
				:required="required"
				:aria-invalid="invalid"
				:aria-describedby="describedBy" />
			<label class="aform_field-label" :for="uuid">{{ label }}</label>
			<p v-show="errorText" :id="errorId" class="aform_error" role="alert">{{ errorText }}</p>
		</template>
	</div>
</template>

<script setup lang="ts">
import { computed } from 'vue'

import { fieldErrorA11y } from '@/composables/fieldErrorA11y'

const {
	label,
	required,
	mode,
	uuid,
	errors,
	validation = { errorMessage: '' },
} = defineProps<{
	label?: string
	required?: boolean
	mode?: 'edit' | 'read' | 'display'
	uuid?: string
	errors?: string[]
	validation?: { errorMessage: string }
}>()

const errorText = computed(() => (errors?.length ? errors.join('; ') : (validation.errorMessage ?? '')))
const { errorId, describedBy, invalid } = fieldErrorA11y(uuid, errorText)

const inputNumber = defineModel<number | null>()

const boxNumber = computed({
	get: () => inputNumber.value,
	set: (value: number | '') => (inputNumber.value = value === '' ? null : value),
})
</script>
