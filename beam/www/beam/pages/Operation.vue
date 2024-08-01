<template>
	<h1>Operation</h1>
	<div class="container">
		<div class="box">
			{{ operationDetails.instructions }}
		</div>
		<div class="box fix-height">
			<b class>{{ operationDetails.startTime }}</b>
			<button :disabled="!operationDetails.hasStarted" @click="startOperation">Start timer</button>
			<button :disabled="operationDetails.hasStarted" @click="stopOperation">Done</button>
		</div>
	</div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'

const operationDetails = ref({})

onMounted(() => {
	// TODO: update this value with the correct API call
	operationDetails.value = {
		instructions:
			'In the heart of the bustling city, a small café nestled between towering skyscrapers offered a serene escape from the urban rush. The aroma of freshly brewed coffee wafted through the air, mingling with the faint scent of pastries baking in the oven. Patrons, a mix of hurried professionals and leisurely readers, filled the cozy space, creating a hum of quiet conversations and the occasional clatter of porcelain cups. Sunlight streamed through the large windows, casting a warm glow on the rustic wooden tables and mismatched chairs. It was a haven of tranquility where time seemed to slow, if only for a moment, allowing everyone to savor the simple pleasures of life.',
		hasStarted: true, // or True
		startTime: '00:00:00', // or "hh:mm:ss"
	}
})

const startOperation = () => {
	// your action here
	alert('Timer Started')
}

const stopOperation = () => {
	// your action here
	alert('Timer Stopped')
}
</script>

<style scoped>
b {
	display: flex;
	justify-content: center;
	align-items: center;
}
.container {
	display: flex;
	gap: 20px;
	/* Space between the boxes */
}

.box {
	padding: 2rem;
	margin: 0.5rem;
	font-size: 100%;
	border: 2px solid gray;
	outline: 2px solid transparent;
	flex: 1;
	min-width: 100px;
}

.fix-height {
	height: 7rem;
	font-size: 150%;
	text-align: center;
	display: grid;
	grid-template-columns: repeat(3, 1fr);
	gap: 20px;
}
</style>
