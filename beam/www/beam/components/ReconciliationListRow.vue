<template>
	<li :tabindex="item.count ? -1 : 0" class="beam_list-item reconciliation-list-row" @click="onRowClick">
		<div class="beam_list-text">
			<label class="beam--bold">{{ item.label || item.item_code }}</label>
			<p v-if="item.description">{{ item.description }}</p>
		</div>

		<div v-if="item.count && item.count.count == null" class="beam_item-count reconciliation-count-pending">
			<span class="reconciliation-count-empty" aria-hidden="true"></span>
		</div>
		<ItemCount
			v-else-if="item.count"
			ref="itemCount"
			:model-value="item.count.count as number"
			:debounce="item.debounce"
			:denominator="0"
			:editable="true"
			@update:model-value="onCountChange" />

		<BeamBtn
			class="clear-button reconciliation-row-remove"
			type="button"
			aria-label="Skip counting this item"
			@click.stop="emit('remove')">
			X
		</BeamBtn>
	</li>
</template>

<script setup lang="ts">
import ItemCount from '@/components/ItemCount.vue'
import type { ListViewItem } from '@/types/stonecrop.js'
import { nextTick, ref } from 'vue'

import type { ReconciliationListRow as ReconciliationRow } from '@/utils/reconciliation'

const props = defineProps<{ item: ReconciliationRow & ListViewItem }>()
const emit = defineEmits<{ remove: []; update: [item: ReconciliationRow & ListViewItem] }>()
const itemCount = ref<InstanceType<typeof ItemCount> | null>(null)

const onRowClick = async () => {
	if (props.item.count && props.item.count.count == null) {
		emit('update', { ...props.item, count: { ...props.item.count, count: 0 } })
		await nextTick()
	}
	itemCount.value?.focus()
}

const onCountChange = (value: number) => {
	if (!props.item.count) return
	emit('update', {
		...props.item,
		count: {
			...props.item.count,
			count: value,
		},
	})
}
</script>

<style scoped>
.beam_list-item.reconciliation-list-row {
	padding: 0.625rem;
	border-bottom: 1px solid var(--sc-row-border-color);
	max-width: 100%;
	box-sizing: border-box;
	display: flex;
	flex-flow: row nowrap;
	justify-content: space-between;
	align-items: center;
	gap: 0.75rem;
	cursor: pointer;
	outline: 2px solid transparent;
	outline-offset: -1px;
	list-style: none;
}

.beam_list-item.reconciliation-list-row:focus,
.beam_list-item.reconciliation-list-row:focus-within {
	outline: 2px solid var(--sc-focus-cell-outline);
	background-color: var(--sc-focus-cell-background);
}

.beam_list-text {
	text-overflow: ellipsis;
	white-space: nowrap;
	overflow: hidden;
	flex: 1 1 auto;
	min-width: 0;
	font-size: 0.875rem;
	color: var(--sc-primary-text-color);
}

.beam_list-item.reconciliation-list-row label,
.beam_list-item.reconciliation-list-row p {
	overflow: hidden;
	text-overflow: ellipsis;
	width: 100%;
	display: block;
	margin: 0;
}

.beam_list-item.reconciliation-list-row label {
	display: block;
}

.reconciliation-list-row :deep(.beam_item-count) {
	flex-shrink: 0;
	white-space: nowrap;
	font-size: 1.3125rem;
}

.reconciliation-list-row :deep(.beam--alert) {
	color: var(--sc-primary-text-color);
}

.reconciliation-row-remove {
	flex-shrink: 0;
	margin: 0;
	padding: 0.5rem 0.75rem !important;
}

.reconciliation-count-pending {
	flex-shrink: 0;
	white-space: nowrap;
	font-size: 1.3125rem;
	color: var(--sc-primary-text-color);
}

.reconciliation-count-empty {
	display: inline-block;
	min-width: 1.25rem;
}
</style>
