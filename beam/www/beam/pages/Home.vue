<template>
	<nav>
		<ListView :items="home" />
	</nav>
</template>

<script setup lang="ts">
import { ref } from 'vue'

const home = ref([
	{
		label: 'Manufacture',
		route: 'beam#/manufacture',
		linkComponent: 'ListAnchor',
	},
	{
		label: 'Transfer',
		route: 'beam#/transfer',
		linkComponent: 'ListAnchor',
	},
	{
		label: 'Receive',
		route: 'beam#/receive',
		linkComponent: 'ListAnchor',
	},
	{
		label: 'Ship',
		route: 'beam#/ship',
		linkComponent: 'ListAnchor',
	},
	{
		label: 'Repack',
		route: 'beam#/repack',
		linkComponent: 'ListAnchor',
	},
])
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
