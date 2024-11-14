<template>
	<div :class="`button-${buttons.length} control-buttons`">
		<BeamBtn
			v-for="(button, index) in buttons"
			:key="index"
			@click="button.action"
			:disabled="button.disabled"
			v-show="!button.hidden"
			:style="{
				'background-color': !button.disabled ? button.color?.background || 'inherit' : 'inherit',
				color: !button.disabled ? button.color?.text || 'inherit' : 'inherit',
				cursor: !button.disabled ? 'auto' : 'not-allowed',
			}">
			{{ button.label }}
		</BeamBtn>
	</div>
</template>

<script setup lang="ts">
const props = defineProps<{
	buttons: Array<{ label: string; action: () => void; disabled: boolean; hidden: boolean; color: object | undefined }>
}>()
</script>

<style scoped>
.control-buttons {
	display: flex;
	flex-wrap: wrap-reverse;
	flex-direction: row-reverse;
	gap: 0.5rem;
	width: calc(100% - 1rem);
	padding: 0.5rem;
	position: fixed;
	bottom: 0;
	justify-content: space-between;
}

.control-buttons > button {
	flex: 1 1 calc(50% - 0.5rem);
	min-width: fit-content;
	letter-spacing: 0.05rem;
	font-weight: bold;
}

.control-buttons > button:last-child {
	flex: 1 1 100%;
}
</style>
