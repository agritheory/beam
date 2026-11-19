<template>
	<ul class="beam_list-view">
		<li v-for="item in items" :key="rowKey(item)">
			<template v-if="item.linkComponent === 'BeamDayDivider'">
				<BeamDayDivider :item="item" />
			</template>
			<template v-else-if="showInspection(item)">
				<InspectionLine :to="inspectionRoute(item)" :state="inspectionState(item)">
					<ListItem :item="item" @update="handleUpdate" />
				</InspectionLine>
			</template>
			<template v-else-if="item.linkComponent === 'ListAnchor' && item.route">
				<ListAnchor :to="item.route">
					<ListItem :item="item" @update="handleUpdate" />
				</ListAnchor>
			</template>
			<template v-else>
				<ListItem :item="item" @update="handleUpdate" />
			</template>
		</li>
	</ul>
</template>

<script setup lang="ts">
import type { ListViewItem } from '@/types/stonecrop.js'

import InspectionLine from '@/components/InspectionLine.vue'

defineProps<{ items: ListViewItem[] }>()
const emit = defineEmits<{ update: [item: ListViewItem]; scrollbottom: [] }>()

type InspectionRow = ListViewItem & {
	inspectionRoute?: string
	inspectionIndicator?: boolean
	inspectionState?: string
	route?: string
	barcode?: string
	label?: string
}

const rowKey = (item: InspectionRow) => item.barcode || item.label || item.inspectionRoute || item.route || ''

const inspectionRoute = (item: InspectionRow) =>
	item.inspectionRoute || (item.linkComponent === 'InspectionLine' ? item.route : undefined)

const inspectionState = (item: InspectionRow) => item.inspectionState

const showInspection = (item: InspectionRow) =>
	Boolean(item.inspectionIndicator || inspectionRoute(item) || item.linkComponent === 'InspectionLine')

const handleUpdate = (item: ListViewItem) => emit('update', item)
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
