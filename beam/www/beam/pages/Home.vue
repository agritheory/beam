<template>
	<Navbar @click="logout">
		<template #title>
			<h2 class="nav-title">{{ companyName }}</h2>
		</template>
		<template #navbaraction>Log out</template>
	</Navbar>

	<nav>
		<ListView :items="homeList" />
	</nav>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'

import { useBeamStore } from '@/stores/beam'
import type { ListViewItem } from '@/types'

const store = useBeamStore()

const companyName = ref('')
const home = ref<ListViewItem[]>([])

onMounted(async () => {
	const getHome = await store.getHome()
	home.value = getHome.data.routes
	companyName.value = getHome.data.company
})

const homeList = computed(() => {
	const items = []
	home.value.forEach(item => {
		item.linkComponent = 'ListAnchor'
		items.push(item)
	})
	return items
})

const logout = async () => {
	await store.logout()
}
</script>

<style scoped>
nav {
	padding-top: 0.5rem;
}

li {
	list-style: none;
	padding: 2rem;
	margin: 0.5rem;
	font-size: 150%;
	border: 2px solid gray;
	outline: 2px solid transparent;
}

li:active {
	outline: 2px solid gray;
}

.home-nav {
	display: block;
}
</style>
