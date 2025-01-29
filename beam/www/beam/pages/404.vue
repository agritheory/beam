<template>
	<Navbar>
		<template #title>
			<h1></h1>
		</template>
		<template #navbaraction>
			<RouterLink :to="{ name: 'home' }">Home</RouterLink>
		</template>
	</Navbar>

	<p>Page not found</p>
</template>

<style scoped>
nav {
	padding-top: 0.5rem;
}

p {
	font-size: 125%;
	text-align: center;
}
</style>
