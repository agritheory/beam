<template>
    <h1>Work Order</h1>
    <div @click="redirectToJobCard(orderId = workOrder)" v-for="workOrder in workOrders">
        <li>{{ workOrder }}</li>
    </div>
</template>
<script setup>
import { onMounted, ref } from 'vue';
import { useRouter } from 'vue-router';

const workOrders = ref([]); // add correct class
const router = useRouter();

onMounted(() => {
    // update this value with the correct API call
    workOrders.value = ["Order 1", "Order 2", "Order 3", "Order 4", "Order 5", "Order 6"]
})
const redirectToJobCard = (orderId) => {
    router.push({ name: 'job_card', params: { orderId } });
};

</script>
<style scoped>
div {
    padding-top: 0.5rem;
}

li {
    list-style: none;
    padding: 2rem;
    margin: 0.5rem;
    font-size: 150%;
    border: 2px solid gray;
    outline: 2px solid transparent;
}

li:active {
    outline: 2px solid gray;
}
</style>
