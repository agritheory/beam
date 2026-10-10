<template>
	<BeamFilterOption title="Assigned" :choices="users" @select="filter" />
</template>

<script setup lang="ts">
import type { BeamFilterChoice } from '@stonecrop/beam'
import { onMounted, ref } from 'vue'

import { useBeamStore } from '@/stores/beam'
import type { User } from '@/types'

declare const frappe: {
	session: {
		user: string
	}
}

const { filter } = defineProps<{
	filter: (choice: BeamFilterChoice) => void | Promise<void>
}>()

const store = useBeamStore()
const users = ref<BeamFilterChoice[]>([{ label: 'All', value: 'all' }])

onMounted(async () => {
	const enabledUsers = await store.getAll<User>('User', {
		filters: JSON.stringify([
			['enabled', '=', true],
			['name', 'not in', ['Administrator', 'Guest']],
		]),
		fields: JSON.stringify(['name', 'first_name', 'last_name']),
	})

	const userChoices = enabledUsers.map(user => ({
		label: user.last_name ? `${user.first_name} ${user.last_name}` : user.first_name,
		value: user.name,
	})) as BeamFilterChoice[]

	const currentUser = frappe.session.user
	const currentUserIndex = enabledUsers.findIndex(user => user.name === currentUser)

	if (currentUserIndex > -1) {
		users.value = [
			{ label: 'All', value: 'all' },
			{ label: 'Me', value: currentUser },
			...userChoices.slice(0, currentUserIndex),
			...userChoices.slice(currentUserIndex + 1),
		]
	} else {
		users.value = [{ label: 'All', value: 'all' }, ...userChoices]
	}
})
</script>
