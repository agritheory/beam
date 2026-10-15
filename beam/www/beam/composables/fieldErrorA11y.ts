// Copyright (c) 2026, AgriTheory and contributors
// For license information, please see license.txt

import { computed, type ComputedRef } from 'vue'

export function fieldErrorA11y(
	uuid: string | undefined,
	errorText: ComputedRef<string>,
	extraDescribedBy?: ComputedRef<string | undefined>
) {
	const errorId = computed(() => (uuid ? `${uuid}-error` : undefined))
	const hasError = computed(() => Boolean(errorText.value))
	const describedBy = computed(() => {
		if (hasError.value && errorId.value) return errorId.value
		return extraDescribedBy?.value
	})
	const invalid = computed(() => (hasError.value ? true : undefined))

	return { errorId, hasError, describedBy, invalid }
}
