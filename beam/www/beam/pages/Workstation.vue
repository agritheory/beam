<template>
	<Navbar @click="handlePrimaryAction">
		<template #title>
			<h1 class="nav-title">Workstations</h1>
		</template>
		<template #navbaraction>Done</template>
	</Navbar>
	<ListView :items="workstations" />
</template>
<script setup>
import { ref, onMounted } from 'vue'

import { Navbar } from '@stonecrop/beam'

onMounted(() => {})

const handlePrimaryAction = () => {}
</script>
