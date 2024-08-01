<template>
	<Navbar @click="handlePrimaryAction">
		<template #title>
			<h1 class="nav-title">Workstations</h1>
		</template>
		<template #navbaraction>Done</template>
	</Navbar>
	<ListView :items="workstations" />
</template>

<script setup lang="ts">
import { Navbar } from '@stonecrop/beam'

const handlePrimaryAction = () => {}
const workstations = ['Manufacture', 'Receive', 'Repack', 'Ship']
</script>
