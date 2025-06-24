<template>
	<li tabindex="0" class="beam_list-item">
		<div class="beam_list-text">
			<label class="beam--bold">{{ listItem.label }}</label>
			<p>{{ listItem.description }}</p>
		</div>

		<ItemCount
			v-if="listItem.count"
			v-model="listItem.count.count"
			:debounce="listItem.debounce"
			:denominator="listItem.count.of"
			:editable="true"
			:uom="listItem.count.uom" />
		<ItemCheck v-if="listItem.hasOwnProperty('checked')" v-model="listItem.checked" />
	</li>
</template>

<script setup lang="ts">
import ItemCount from './ItemCount.vue'
import { ref, watch } from 'vue'

type ListViewItem = {
	barcode?: string
	checked?: boolean
	count?: {
		count: number
		of: number
		uom?: string
	}
	date?: string
	dateFormat?: string
	debounce?: number
	description?: string
	label?: string
	linkComponent?: string
	route?: string
}

const { item } = defineProps<{ item: ListViewItem }>()
const emit = defineEmits<{ update: [item: ListViewItem] }>()

const listItem = ref(item)

watch(
	listItem,
	value => {
		emit('update', value)
	},
	{ deep: true }
)
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

	&:focus {
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
