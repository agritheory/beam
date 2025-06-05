<template>
	<Navbar @click="store.logout">
		<template #title>
			<h2>{{ companyName }}</h2>
		</template>
		<template #navbaraction>Log out</template>
	</Navbar>

	<ScanOutput v-show="store.scanner.config.show_scan_output" />

	<nav>
		<ListView :items="homeList" />
	</nav>
</template>

<script setup lang="ts">
import type { ListViewItem } from '@stonecrop/beam'
import { computed, ref, onMounted } from 'vue'

import ScanOutput from '@/components/ScanOutput.vue'
import { useBeamStore } from '@/stores/beam'

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
