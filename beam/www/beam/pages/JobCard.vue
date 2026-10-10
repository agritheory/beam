<template>
	<li v-for="operation in store.form.operations">
		<RouterLink :to="{ name: 'operation', params: { id: route.params.id, operationId: operation.name } }">
			<span>{{ operation.operation }}</span>
			<span class="right-align"> ({{ operation.completed_qty }} / {{ store.form.qty }})</span>
		</RouterLink>
	</li>
</template>

<script setup lang="ts">
import { useRoute } from 'vue-router'

import { useBeamStore } from '@/stores/beam'

const route = useRoute()
const store = useBeamStore()
</script>

<style scoped>
.right-align {
	margin-left: auto;
}
</style>
