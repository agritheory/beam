<template>
	<Teleport to="#beam_modal_outlet" defer>
		<div v-show="showModal" class="beam_modal">
			<BeamBtn @click="$emit('closemodal')">Close Modal</BeamBtn>
			<slot @closemodal="$emit('closemodal')" @confirmmodal="$emit('confirmmodal')"></slot>
		</div>
	</Teleport>
</template>

<script setup lang="ts">
defineEmits<{ closemodal: []; confirmmodal: [] }>()
defineProps<{ showModal: boolean }>()
</script>

<style scoped>
.beam_modal {
	position: fixed;
	top: 0;
	right: 0;
	bottom: 0;
	left: 0;
	background-color: rgba(0, 0, 0, 0.5);
	backdrop-filter: blur(2px);
	z-index: 200;
	text-align: center;
	padding: 1.25rem;
}
</style>
