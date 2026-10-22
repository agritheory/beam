<template>
	<button class="beam_btn">
		<slot>Action</slot>
	</button>
</template>

<style scoped>
.beam_btn {
	font-size: 0.875rem;
	text-align: center;
	padding: 0.3125rem 0.75rem;
	border: 1px solid var(--sc-btn-border);
	color: var(--sc-btn-label-color);
	background-color: var(--sc-btn-color);
	cursor: pointer;
	font-family: var(--sc-font-family);

	&:hover,
	&:active {
		background-color: var(--sc-btn-hover);
	}
}
</style>
<style>
.beam_btn a:link,
.beam_btn a:visited,
.beam_btn a:hover,
.beam_btn a:active {
	text-decoration: none;
	color: var(--sc-btn-label-color);
}
</style>
