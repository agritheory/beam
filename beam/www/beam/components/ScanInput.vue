<template>
	<div id="scan_input"></div>
</template>

<script setup lang="ts">
import onScan from 'onscan.js'
import type { OnScan } from 'onscan.js'
import { onMounted, onUnmounted } from 'vue'

const emit = defineEmits<{ scanInstance: [instance: OnScan] }>()
const props = defineProps<{
	scanHandler: (barcode: string, qty: number) => void
}>()

onMounted(() => {
	const instance = onScan.attachTo(window, { onScan: props.scanHandler })
	emit('scanInstance', instance)
})

onUnmounted(() => {
	onScan.detachFrom(window)
})
</script>
