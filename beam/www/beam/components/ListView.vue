<template>
	<ul class="beam_list-view" v-bind="$attrs">
		<li v-for="{ item, key } in rows" :key="key">
			<template v-if="item.linkComponent == 'BeamDayDivider'">
				<BeamDayDivider :item="item"></BeamDayDivider>
			</template>

			<template v-else-if="item.linkComponent">
				<component :is="item.linkComponent" :to="item.route" tabindex="-1">
					<ListItem :item="item" @update="handleUpdate"></ListItem>
				</component>
			</template>

			<template v-else>
				<ListItem :item="item" @update="handleUpdate"></ListItem>
			</template>
		</li>
	</ul>
	<div class="begin" v-if="showEmpty">
		<span>{{ filtered ? filteredText : emptyText }}</span>
	</div>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'

import BeamDayDivider from './BeamDayDivider.vue'
import ListItem from './ListItem.vue'
import type { ListViewItem } from '@/types/stonecrop.js'

defineOptions({ inheritAttrs: false })

const props = withDefaults(
	defineProps<{
		items: ListViewItem[]
		emptyText?: string
		filteredText?: string
		filtered?: boolean
		loaded?: boolean
	}>(),
	{
		emptyText: 'Nothing to show',
		filteredText: 'No results for these filters',
		filtered: false,
		loaded: true,
	}
)
const emit = defineEmits<{ update: [item: ListViewItem]; scrollbottom: [] }>()

const showEmpty = computed(() => props.loaded && props.items.length === 0)

const rows = computed(() => {
	const seen = new Map<string, number>()
	return props.items.map(item => {
		const base = String(item.barcode || item.label || '')
		const occurrence = seen.get(base) ?? 0
		seen.set(base, occurrence + 1)
		return { item, key: occurrence ? `${base}#${occurrence}` : base }
	})
})

onMounted(() => {
	window.addEventListener('scroll', handleScroll)
})

onUnmounted(() => {
	window.removeEventListener('scroll', handleScroll)
})

const handleUpdate = (item: ListViewItem) => emit('update', item)
const handleScroll = () => {
	const scrollHeightDifference = document.documentElement.scrollHeight - window.innerHeight
	const scrollposition = document.documentElement.scrollTop
	if (scrollHeightDifference - scrollposition <= 2) {
		emit('scrollbottom')
	}
}
</script>

<style scoped>
.beam_list-view {
	font-family: var(--sc-font-family);
	list-style-type: none;
	margin-top: 1px;
	margin-left: var(--sc-list-margin);
	margin-right: var(--sc-list-margin);
	padding: 0;
}

ul.beam_list-view:last-of-type {
	padding-bottom: 2.5em;
}

.begin {
	width: 100%;
	text-align: center;
	font-size: 1rem;
	color: var(--sc-primary-text-color);
	padding: 1rem var(--sc-list-margin);
	box-sizing: border-box;
	text-wrap: balance;
}
</style>
