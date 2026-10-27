<template>
	<div class="beam_metadata">
		<div class="beam_metadata_content">
			<slot>
				<div class="beam_metadata_header beam_metadata--two-column"></div>
				<div class="beam_metadata_block">
					<p class="beam_metadata_heading">
						Status:
						<span :class="{ alert: !order.complete }" class="beam_metadata--normal">{{
							order.complete ? 'Complete' : 'In Progress'
						}}</span>
					</p>
				</div>
				<div class="beam_metadata_shipping beam_metadata_block">
					<div class="beam_metadata_source">
						<p class="beam_metadata_heading">Source</p>
					</div>

					<div class="beam_metadata_source">
						<p class="beam_metadata_heading">Receiving</p>
					</div>
				</div>
			</slot>
		</div>
		<hr />
	</div>
</template>

<script setup lang="ts">
defineProps<{
	order: {
		orderNumber: string
		product: string
		quantity: number
		total: number
		complete: boolean
	}
}>()
</script>

<style scoped>
.beam_metadata {
	/* margin:3.125rem; */
	box-sizing: border-box;
	display: flex;
	flex-direction: column;
	max-height: 100vh;
	color: var(--sc-primary-text-color);
	font-family: var(--sc-font-family);
}
.beam_metadata_content {
	padding-top: 10px;
}
.beam_metadata_header {
	display: flex;
	flex-direction: row;
	align-items: baseline;
	padding: 0px 30px 0px 30px;
	justify-content: space-between;
}
.beam_metadata_count {
	font-size: 1.5rem;

	& p {
		margin: 0;
	}
}
.beam_metadata_header-order-num {
	font-weight: bold;
	font-size: 1.5rem;
}
.beam_metadata_block {
	padding: 0px 30px;
	margin: 10px 0;
}

.beam_metadata_shipping {
	display: flex;
	flex-direction: row;
	align-items: baseline;
	justify-content: space-between;

	& p {
		line-height: 1.5rem;
	}
}
@media screen and (max-width: 600px) {
	.beam_metadata_shipping {
		flex-direction: column;
	}
}

.beam_metadata_component_header {
	display: flex;
	flex-direction: row;
	justify-content: space-between;
	align-items: baseline;
}
.beam_metadata_components {
	overflow: scroll;
}
hr {
	display: block;
	height: 1px;
	border: 0;
	border-top: 1px solid var(--sc-row-border-color);
	margin: 1em 0;
	padding: 0;
}
</style>
<style>
.beam_metadata_heading {
	font-size: 1.125rem;
	font-weight: bold;
	margin: 0.625rem 0;
	color: var(--sc-primary-text-color);
}
</style>
