<template>
	<nav>
		<ListView :items="home" />
	</nav>
</template>

<script setup lang="ts">
const home = [
	{
		label: 'Manufacture',
		route: '#/manufacture',
		linkComponent: 'ListAnchor',
	},
	{
		label: 'Demand',
		route: '#/demand',
		linkComponent: 'ListAnchor',
	},
	{
		label: 'Move',
		route: '#/move',
		linkComponent: 'ListAnchor',
	},
	{
		label: 'Receive',
		route: '#/receive',
		linkComponent: 'ListAnchor',
	},
	{
		label: 'Ship',
		route: '#/ship',
		linkComponent: 'ListAnchor',
	},
	{
		label: 'Repack',
		route: '#/repack',
		linkComponent: 'ListAnchor',
	},
]
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
