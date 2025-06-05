<template>
	<!-- filters section -->
	<BeamFilter>
		<BeamFilterOption
			title="Status"
			:choices="[
				{ label: 'All', value: 'all' },
				{ label: 'Unallocated', value: 'unallocated' },
				{ label: 'Partially Allocated', value: 'partially_allocated' },
				{ label: 'Soft Allocated', value: 'soft_allocated' },
			]"
			@select="setStatusFilter" />
		<BeamFilterOption
			title="Delivery Date"
			:choices="[
				{ label: 'All', value: 'all' },
				{ label: 'Past', value: 'past' },
				{ label: 'Today', value: 'today' },
				{ label: 'Future', value: 'future' },
			]"
			@select="setDateFilter" />
		<UserFilter :filter="setUserFilter" />
	</BeamFilter>
</template>

<script setup lang="ts">
import type { BeamFilterChoice } from '@stonecrop/beam'
import { ref } from 'vue'

import UserFilter from '@/components/UserFilter.vue'
import { DemandFilter } from '@/types'

const emit = defineEmits<{ filter: [filters: DemandFilter] }>()
const filters = ref<DemandFilter>({})

const setStatusFilter = (choice: BeamFilterChoice) => {
	switch (choice.value) {
		case 'all':
			delete filters.value.status
			break
		case 'unallocated':
			filters.value.status = ['in', ['Unallocated', '']]
			break
		case 'partially_allocated':
			filters.value.status = 'Partially Allocated'
			break
		case 'soft_allocated':
			filters.value.status = 'Soft Allocated'
			break
	}
	emit('filter', filters.value)
}

const setDateFilter = (choice: BeamFilterChoice) => {
	const today = new Date()
	const todayString = today.toISOString().split('T')[0]
	switch (choice.value) {
		case 'all':
			delete filters.value.date
			break
		case 'past':
			filters.value.date = ['<', todayString]
			break
		case 'today':
			filters.value.date = todayString
			break
		case 'future':
			filters.value.date = ['>', todayString]
			break
	}
	emit('filter', filters.value)
}

const setUserFilter = (choice: BeamFilterChoice) => {
	switch (choice.value) {
		case 'all':
			delete filters.value.user
			break
		default:
			filters.value.user = choice.value
			break
	}
	emit('filter', filters.value)
}
</script>
