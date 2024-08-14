<template>
	<h3>Work Orders</h3>
	<ListView :items="workOrders" />
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import type { WorkOrder } from '../types'

const workOrders = ref<WorkOrder[]>([])

onMounted(async () => {
	// avoid CSRF-token errors on reloading a page
	frappe.csrf_token = window.csrf_token

	const response = await frappe.call({
		method: 'frappe.client.get_list',
		args: {
			doctype: 'Work Order',
			order_by: 'creation',
			fields: ['name', 'item_name AS label', 'qty', 'produced_qty'],
		},
	})
	response.message.forEach(row => {
		row.count = { count: row.produced_qty, of: row.qty }
		row.linkComponent = 'ListAnchor'
		row.route = `#/work_order/${row.name}`
	})
	workOrders.value = response.message as WorkOrder[]
})
</script>
