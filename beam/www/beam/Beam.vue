<template>
	<!-- setup modal behaviour -->
	<BeamModal @confirmmodal="confirmModal" @closemodal="closeModal" :showModal="showModal">
		<Confirm @confirmmodal="confirmModal" @closemodal="closeModal" />
	</BeamModal>
	<BeamModalOutlet @confirmmodal="confirmModal" @closemodal="closeModal"></BeamModalOutlet>

	<!-- setup scan input listeners -->
	<ScanInput :scanHandler="scan" @scanInstance="registerInstance" />
	<Camera ref="cameraRef" :allow-photo="allowPhoto" @scan="scan" @photos-captured="handlePhotosCaptured" />

	<!-- setup main view -->
	<RouterView />
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'

import Camera from '@/components/Camera.vue'
import { useBeamStore } from '@/stores/beam'
import { useScanStore } from '@/stores/scan'
import type { BeamWindow } from '@/types'

declare const window: BeamWindow

const router = useRouter()
const beamStore = useBeamStore()
const scanStore = useScanStore()
const showModal = ref(false)
const cameraRef = ref<InstanceType<typeof Camera> | null>(null)

// Route meta (including cameraPhoto) comes from hooks.py via yarn build.
// Prefer useRouter() here — pinia's markRaw(router) is for stores, not this component.
const allowPhoto = computed(() => Boolean(router.currentRoute.value.meta.cameraPhoto))

const documentKey = computed(() => {
	const { meta, params, query } = router.currentRoute.value
	const id = query.id || params.id || ''
	return `${meta.doctype ?? ''}:${id}`
})

watch(documentKey, () => {
	cameraRef.value?.resetPhotos()
})

watch(
	() => beamStore.camera.pendingPhotos,
	files => cameraRef.value?.syncCapturedPhotos(files)
)

const scan = async (barcode: string, qty: number) => {
	await scanStore.scan(barcode, qty)
}

const handlePhotosCaptured = (files: File[]) => {
	beamStore.setPendingPhotos(files)
}

const closeModal = () => (showModal.value = false)
const confirmModal = () => (showModal.value = false)
const registerInstance = (instance: any) => (window.scanner = instance)
</script>

<style>
* {
	font-family: var(--sc-font-family) !important;
}

.navbar-action a {
	color: inherit;
	text-decoration: none;
}

.navbar-action a:visited {
	color: inherit;
	text-decoration: none;
}

.navbar-action a:hover {
	color: inherit;
	text-decoration: none;
}

.navbar-action a:active {
	color: inherit;
	text-decoration: none;
}

:root {
	--sc-input-active-border-color: #333333;
	--sc-input-border-color: #cccccc;
	--sc-row-color-zebra-light: #f2f2f2;
	--sc-focus-cell-outline: #333333;
	--sc-focus-cell-background: #f2f2f2;
	--sc-beam-danger-fill: #c02718;
	--sc-beam-warning-text: #6b4a00;
	--sc-form-background: #fafafa;
	--sc-input-field-background: #f2f2f2;
	--sc-cell-text-color: #3a3c41;
	--sc-input-label-color: #666666;
	--sc-input-active-label-color: #333333;
	--sc-overlay-background: #ffffff;
	--sc-row-hover-color: #e6e6e6;
	--sc-btn-hover: #f2f2f2;
	--beam-footer-rows: 1;
	--beam-footer-height: calc(var(--beam-footer-rows) * 3.25rem + 1rem + env(safe-area-inset-bottom, 0px));
}

.beam_btn {
	transition: background-color 120ms ease-out;
}

.beam_btn:focus-visible {
	outline: 2px solid var(--sc-focus-cell-outline);
	outline-offset: 2px;
}

@media (prefers-reduced-motion: reduce) {
	.beam_btn,
	.control-buttons > button,
	.operation-action-btn {
		transition: none !important;
	}
}
</style>
