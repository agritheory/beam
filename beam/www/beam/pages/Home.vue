<template>
    <nav>
        <RouterLink class="home-nav" to="/workstation">
            <li>Workstations</li>
        </RouterLink>
        <RouterLink class="home-nav" to="/work_order">
            <li>Work Orders</li>
        </RouterLink>
        <RouterLink class="home-nav" to="/receive">
            <li>Receive</li>
        </RouterLink>
        <RouterLink class="home-nav" to="/ship">
            <li>Ship</li>
        </RouterLink>
        <RouterLink class="home-nav" to="/transfer">
            <li>Transfer</li>
        </RouterLink>
        <RouterLink class="home-nav" to="/manufacture">
            <li>Manufacture</li>
        </RouterLink>
        <RouterLink class="home-nav" to="/repack">
            <li>Repack</li>
        </RouterLink>
    </nav>
</template>
<script setup></script>
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
