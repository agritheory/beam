<template>
    <ListView :items="listItems" />
</template>

<script setup lang="ts">
import { defineProps, ref, watchEffect } from 'vue';
import type { ListTransferItem, ListViewItem } from '../types'

const props = defineProps<{
    items: ListTransferItem[],
    workOrderId: string | string[],
}>()

const listItems = ref<ListViewItem[]>([])

watchEffect(() => {
    listItems.value = props.items?.map(it => ({
        label: it.item_name,
        description: `${it.source_warehouse} > ${it.source_warehouse}`,
        count: {
            count: 0,
            of: it.required_qty
        }
    }))
})

</script>
