<template>
	<h1 class="beam_header">
		<slot></slot>
	</h1>
</template>

<style scoped>
.beam_header {
	border: 1px solid transparent;
	text-align: left;
	font-size: 1.125rem;
	color: var(--sc-primary-text-color);
	margin: 0;
	padding: 0;
	font-family: var(--sc-font-family);
}
</style>
