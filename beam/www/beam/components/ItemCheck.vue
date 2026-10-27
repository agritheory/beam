<template>
	<label class="container">
		<input v-model="value" type="checkbox" tabindex="-1" />
		<div class="checkmark" tabindex="0"></div>
	</label>
</template>

<script setup lang="ts">
const value = defineModel<boolean>({ default: false })
</script>

<style scoped>
.container {
	display: block;
	position: relative;
	padding-left: 2.5ch;
	margin: 0;
	margin-top: 0.5rem;
	cursor: pointer;
	font-size: 2rem;
	-webkit-user-select: none;
	-moz-user-select: none;
	-ms-user-select: none;
	user-select: none;
}

/* hide default checkbox */
.container input {
	position: absolute;
	opacity: 0;
	cursor: pointer;
	height: 0;
	width: 0;
}

.checkmark {
	position: absolute;
	top: 0;
	left: 0;
	height: 2rem;
	width: 2rem;
	background-color: #eee;
	outline: 2px solid transparent;
	border: 1px solid var(--sc-highlight);
}

.container:hover input ~ .checkmark {
	background-color: white;
}

.container input:checked ~ .checkmark {
	background-color: var(--sc-brand-secondary);
}

.checkmark:after {
	content: '';
	position: absolute;
	display: none;
}

.container input:checked ~ .checkmark:after {
	display: block;
}

.container .checkmark:after {
	left: 25%;
	top: 50%;
	width: 0.5rem;
	height: 1rem;
	border: solid var(--sc-text-color);
	border-width: 0 3px 3px 0;
	-webkit-transform: rotate(45deg);
	-ms-transform: rotate(45deg);
	transform: rotate(45deg) translate(-50%, -50%);
}
</style>
