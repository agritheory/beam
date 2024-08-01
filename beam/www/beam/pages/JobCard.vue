<template>
	<h1>Job Cards</h1>

	<li v-for="operation in operations">
		<router-link :to="{ name: 'operation', params: { id: operation.id } }">
			<span>{{ operation.id }}</span>
			<span class="right-align"> ({{ operation.completedOperations }} / {{ operation.maxOperations }})</span>
		</router-link>
	</li>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

import { Operation } from '../types'

const operations = ref<Operation[]>([])

onMounted(() => {
	// TODO: update this value with the correct API call
	operations.value = [
		{
			id: 'operation 1',
			maxOperations: '3',
			completedOperations: '0',
		},
		{
			id: 'operation 2',
			maxOperations: '3',
			completedOperations: '0',
		},
		{
			id: 'operation 3',
			maxOperations: '3',
			completedOperations: '0',
		},
		{
			id: 'operation 4',
			maxOperations: '3',
			completedOperations: '0',
		},
		{
			id: 'operation 5',
			maxOperations: '3',
			completedOperations: '0',
		},
	]
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
