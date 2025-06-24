<template>
	<ul class="beam_list-view">
		<li v-for="item in items" :key="item.barcode || item.label">
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
</template>

<script setup lang="ts">
import { onMounted, onUnmounted } from 'vue'
import ListItem from './ListItem.vue'

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

defineProps<{ items: ListViewItem[] }>()
const emit = defineEmits<{ update: [item: ListViewItem]; scrollbottom: [] }>()

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
</style>
