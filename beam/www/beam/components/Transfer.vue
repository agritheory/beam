<template>
    <div>
        <table class="item-table">
            <thead>
                <tr>
                    <th>Components</th>
                    <th>Quantity</th>
                </tr>
            </thead>
            <tbody>
                <tr v-for="item in items" :key="item.name">
                    <td>{{ item.item_name }}</td>
                    <td>{{ item.transferred_qty }}/{{ item.required_qty }}</td>
                </tr>
            </tbody>
        </table>
    </div>
</template>

<script setup lang="ts">
import { defineProps } from 'vue';
import type { ListTransferItem } from '../types'

const props = defineProps<{
    items: ListTransferItem[],
    workOrderId: string | string[],
}>()

</script>

<style scoped>
.item-table {
    width: 100%;
    border-collapse: collapse;
    background-color: #ffffff;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.item-table th,
.item-table td {
    padding: 12px;
    text-align: left;
    border-bottom: 1px solid #ddd;
}

.item-table th {
    background-color: #f9f9f9;
    font-weight: bold;
}

.item-table tr:nth-child(even) {
    background-color: #f2f2f2;
}

.item-table td {
    font-size: 1rem;
}

.item-table th:last-child {
    text-align: right;
}

.item-table td:last-child {
    text-align: right;
    font-weight: bold;
    color: #007bff;
}
</style>