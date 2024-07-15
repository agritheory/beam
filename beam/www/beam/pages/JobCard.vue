<template>
    <h1>Job Cards</h1>
    <div @click="redirectToJobOperations(operationID = operation)" v-for="operation in operations">
        <li><span>
                {{ operation.operationID }}
            </span>
            <span class="right-align">
                {{ operation.completedOperations }}/{{ operation.maxOperations }}
            </span>
        </li>
    </div>
</template>
<script setup>
import { onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

const route = useRoute();
const router = useRouter();
const operations = ref([{}]);
onMounted(() => {
    // use this to get operations
    console.log("route.params.orderId ---> ", route.params.orderId);

    // update this value with the correct API call
    operations.value = [{
        operationID: "operation 1",
        maxOperations: "3",
        completedOperations: "0"
    }, {
        operationID: "operation 2",
        maxOperations: "3",
        completedOperations: "0"
    }, {
        operationID: "operation 3",
        maxOperations: "3",
        completedOperations: "0"
    }, {
        operationID: "operation 4",
        maxOperations: "3",
        completedOperations: "0"
    }, {
        operationID: "operation 5",
        maxOperations: "3",
        completedOperations: "0"
    }]
})
const redirectToJobOperations = (operationID) => {
    router.push({ name: 'operation', params: { operationID: operationID.operationID } });
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
    border-bottom: 2px solid grey;
    display: flex;
    justify-content: space-between;
    padding: 10px;
}

li:active {
    border-bottom: 2px solid ble;
}
.right-align {
    margin-left: auto;
}
</style>