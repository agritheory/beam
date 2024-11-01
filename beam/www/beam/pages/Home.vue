<template>
	<Navbar @click="logout">
		<template #title>
			<h2 class="nav-title">{{ companyName }}</h2>
		</template>
		<template #navbaraction> Log out </template>
	</Navbar>
	<nav>
		<ListView :items="homeList" />
	</nav>
</template>
<script setup lang="ts">
import { computed, ref, onMounted } from 'vue'
import { useDataStore } from '@/store'

const store = useDataStore()

const companyName = ref('')
const home = ref([])

const homeList = computed(() => {
	let hl = []
	home.value.forEach(r => {
		r.linkComponent = 'ListAnchor'
		hl.push(r)
	})
	return hl
})

const logout = async () => {
	await store.logout()
}

onMounted(async () => {
	let getHome = await store.getHome()
	home.value = getHome.data.routes
	companyName.value = getHome.data.company
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
