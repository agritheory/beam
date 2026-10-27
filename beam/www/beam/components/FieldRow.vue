<template>
	<div class="field-row">
		<div v-if="$slots.prefix" class="field-row__prefix">
			<slot name="prefix" />
		</div>
		<div class="field-row__field">
			<slot />
		</div>
		<div v-if="$slots.suffix" class="field-row__suffix">
			<slot name="suffix" />
		</div>
	</div>
</template>

<script setup lang="ts">
defineSlots<{
	default(): any
	prefix?(): any
	suffix?(): any
}>()
</script>

<style scoped>
.field-row {
	--field-row-height: 2.75rem;
	display: flex;
	align-items: flex-end;
	width: 100%;
	gap: 10px;
}

.field-row__field {
	flex: 1;
	min-width: 0;
}

.field-row__prefix,
.field-row__suffix {
	display: flex;
	gap: 10px;
}

.field-row :deep(.aform_input-field) {
	height: var(--field-row-height);
	font-size: 150%;
	box-sizing: border-box;
}

.field-row__prefix :deep(.beam_btn),
.field-row__suffix :deep(.beam_btn) {
	height: var(--field-row-height);
	width: var(--field-row-height);
	padding: 0;
	display: flex;
	align-items: center;
	justify-content: center;
	box-sizing: border-box;
}
</style>
