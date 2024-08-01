<template>
	<h1>Work Order</h1>

	<li v-for="workOrder in workOrders">
		<router-link :to="{ name: 'job_card', params: { id: workOrder } }">
			{{ workOrder }}
		</router-link>
	</li>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

const workOrders = ref([])

onMounted(() => {
	// TODO: update this value with the correct API call
	workOrders.value = ['Order 1', 'Order 2', 'Order 3', 'Order 4', 'Order 5', 'Order 6']
})
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
