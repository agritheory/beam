<template>
	<div :class="`button-${buttons.length} control-buttons`">
		<BeamBtn
			v-for="(button, index) in buttons"
			:key="index"
			@click="button.action"
			:disabled="button.disabled"
		>
			{{ button.label }}
		</BeamBtn>
	</div>
</template>

<script setup lang="ts">
const props = defineProps<{
	buttons: Array<{ label: string; action: () => void; disabled: boolean }>
}>()
</script>

<style scoped>
.control-buttons {
	display: flex;
	width: calc(100% - 1rem);
	padding: 0.5rem;
	position: fixed;
	bottom: 0;
}

.button-1 {
	justify-content: flex-end;
}

.button-2 {
	justify-content: space-between;
}

.button-3 {
	justify-content: space-between;
}
</style>
