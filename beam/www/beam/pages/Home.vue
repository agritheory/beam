<template>
	<Navbar @click="logout">
		<template #title>
			<h1 class="nav-title">{{ companyName }}</h1>
		</template>
		<template #navbaraction>
			Log out
		</template>
	</Navbar>
	<nav>
		<ListView :items="home" />
	</nav>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useDataStore } from '@/store' 

const store = useDataStore()

const companyName = ref('')
const home = ref([])

const logout = async () => {
	await store.logout()
}

onMounted(async () =>{
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
