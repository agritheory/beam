<template>
    <div class="control-buttons">
        <button @click="handleSave" :disabled="!!stockEntryId">Save</button>
        <button @click="handlePOST('submit')" :disabled="!stockEntryId">Submit</button>
        <button @click="handlePOST('cancel')" :disabled="!stockEntryId">Cancel</button>
    </div>
    <ListView :items="listItems" />
</template>

<script setup lang="ts">
import { defineProps, ref, watchEffect } from 'vue';
import type { ListTransferItem, ListViewItem } from '../types'

const props = defineProps<{
    items: ListTransferItem[],
    workOrderId: string | string[],
}>()

const endpoint = '/api/method/erpnext.manufacturing.doctype.work_order.work_order.make_stock_entry'
const listItems = ref<ListViewItem[]>([])
const stockEntryId = ref<String>("")

const handlePOST = async (method: string) => {
    const status = method === "submit" ? 1 : 2
    const response = await fetch(`/api/resource/Stock Entry/${stockEntryId.value}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'X-Frappe-CSRF-Token': frappe.csrf_token
        },
        body: JSON.stringify({
            docstatus: status
        })
    });

    const res = await response.json();
    if (response.ok) {
        alert(`Document status changed to ${status === 1 ? 'Submitted' : 'Cancelled'}`);
    } else {
        alert(`Error: ${res.exception}`);
    }
}

const handleSave = async () => {
    const response = await fetch(endpoint, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Frappe-CSRF-Token': frappe.csrf_token
        },
        body: JSON.stringify({
            work_order_id: props.workOrderId,
            purpose: 'Material Transfer for Manufacture',
        })
    });

    const { message } = await response.json();
    if (!message) {
        alert("error")
        return
    }

    const create = await fetch(`/api/resource/Stock Entry/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Frappe-CSRF-Token': frappe.csrf_token
        },
        body: JSON.stringify(message)
    });
    const { data } = await create.json();
    if (!data) {
        alert("error 2")
        return
    }

    if (create?.status === 200) {
        stockEntryId.value = data.name
    } else {
        alert("Error")
    }
}

watchEffect(() => {
    listItems.value = props.items?.map(it => ({
        label: it.item_name,
        description: `${it.source_warehouse} > ${it.wip_warehouse}`,
        count: {
            count: it.transferred_qty,
            of: it.required_qty,
        }
    }))
})

</script>

<style scoped>
.control-buttons {
    display: flex;
    justify-content: flex-end;
    gap: 1rem;
}
</style>