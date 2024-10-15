<template>
	<li v-for="operation in store.form.operations">
		<router-link :to="{ name: 'operation', params: { orderId: route.params.orderId, id: operation.name } }">
			<span>{{ operation.operation }}</span>
			<span class="right-align"> ({{ operation.completed_qty }} / {{ store.form.qty }})</span>
		</router-link>
	</li>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'

import { useDataStore } from '@/store'

const route = useRoute()
const store = useDataStore()
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
