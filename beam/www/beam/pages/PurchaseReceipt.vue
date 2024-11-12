<template>
	<Navbar>
		<template #title>
			<h1 class="nav-title">Purchase Receipt</h1>
		</template>
		<template #navbaraction>
			<RouterLink :to="{ name: 'home' }">Home</RouterLink>
		</template>
	</Navbar>
	<div class="box" v-show="items.length">
		<ListView :items="items" />
	</div>
	<!-- <ControlButtons :onCreate="create" :onSubmit="() => {}" :onCancel="() => {}" /> -->
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'

import ControlButtons from '@/components/ControlButtons.vue'
import { useBeamStore } from '@/stores/beam'
import type { ListViewItem, PurchaseReceipt } from '@/types'

const store = useBeamStore()
const items = ref<ListViewItem[]>([])

onMounted(async () => {
	store.form as Partial<PurchaseReceipt>
})

store.$subscribe((mutation, state) => {
	const parentfield = state.form.doctype === 'Work Order' ? 'required_items' : 'items'
	if (parentfield && state.form[parentfield]) {
		items.value = []
		state.form[parentfield].forEach(item => {
			item.wip_warehouse = state.form.wip_warehouse
			items.value.push({
				label: item.item_name,
				description: `${item.warehouse}`,
				count: {
					count: item.received_qty,
					of: item.qty,
				},
			})
		})
	}
})
</script>

<style scoped>
b {
	display: flex;
	justify-content: center;
	align-items: center;
}

.container {
	display: flex;
	gap: 20px;
	/* Space between the boxes */
}

.box {
	padding: 2rem;
	margin: 0.5rem;
	font-size: 100%;
	border: 2px solid gray;
	outline: 2px solid transparent;
	flex: 1;
	min-width: 100px;
}
</style>
