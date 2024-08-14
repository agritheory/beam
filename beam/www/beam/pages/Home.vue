<template>
	<nav>
		<li><router-link class="home-nav" to="/manufacture">Manufacture</router-link></li>
		<li><router-link class="home-nav" to="/workstation">Workstations</router-link></li>
		<li><router-link class="home-nav" to="/receive">Receive</router-link></li>
		<li><router-link class="home-nav" to="/ship">Ship</router-link></li>
		<li><router-link class="home-nav" to="/transfer">Transfer</router-link></li>
		<li><router-link class="home-nav" to="/repack">Repack</router-link></li>
	</nav>
</template>

<script setup lang="ts"></script>

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
