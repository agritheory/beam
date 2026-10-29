<template>
	<li :tabindex="listItem.count ? -1 : 0" class="beam_list-item" @click="focusCount">
		<div class="beam_list-text">
			<label class="beam--bold">{{ listItem.label }}</label>
			<p>{{ listItem.description }}</p>
		</div>

		<ItemCount
			v-if="listItem.count"
			ref="itemCount"
			:model-value="listItem.count.count"
			@update:model-value="onCountUpdate"
			:debounce="listItem.debounce"
			:denominator="listItem.count.of"
			:editable="countEditable"
			:uom="listItem.count.uom" />
		<ItemCheck
			v-if="listItem.hasOwnProperty('checked')"
			:model-value="listItem.checked"
			@update:model-value="onCheckedUpdate" />
	</li>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'

import ItemCount from './ItemCount.vue'
import ItemCheck from './ItemCheck.vue'
import type { ListViewItem } from '@/types/stonecrop.js'

const { item } = defineProps<{ item: ListViewItem }>()
const emit = defineEmits<{ update: [item: ListViewItem] }>()

const listItem = ref(item)
const itemCount = ref<InstanceType<typeof ItemCount> | null>(null)
const countEditable = computed(() => listItem.value.count?.editable ?? !listItem.value.linkComponent)

const focusCount = (event: MouseEvent) => {
	if ((event.currentTarget as HTMLElement).closest('a')) return
	itemCount.value?.focus()
}

watch(
	() => item,
	value => {
		listItem.value = value
	}
)

const onCountUpdate = (count: number) => {
	if (!listItem.value.count) return
	listItem.value.count.count = count
	emit('update', listItem.value)
}

const onCheckedUpdate = (checked: boolean) => {
	listItem.value.checked = checked
	emit('update', listItem.value)
}
</script>

<style scoped>
.beam_list-item {
	padding: 0.625rem;
	border-bottom: 1px solid var(--sc-row-border-color);
	max-width: 100%;
	box-sizing: border-box;
	display: flex;
	flex-flow: row nowrap;
	justify-content: space-between;
	gap: 1.25rem;
	cursor: pointer;
	outline: 2px solid transparent;
	outline-offset: -1px;

	&:focus,
	&:focus-within {
		outline: 2px solid var(--sc-focus-cell-outline);
		background-color: var(--sc-focus-cell-background);
	}
}

.beam_list-text {
	width: 80%;
	text-overflow: ellipsis;
	white-space: nowrap;
	overflow: hidden;
	flex-grow: 1;
	font-size: 0.875rem;
	color: var(--sc-primary-text-color);

	& label,
	& p {
		overflow: hidden;
		text-overflow: ellipsis;
		width: 100%;
		display: block;
	}
}

.beam_list-item label {
	display: block;
}

.beam_list-item p {
	margin: 0;
}
</style>
