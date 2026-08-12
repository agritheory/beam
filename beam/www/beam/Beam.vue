<template>
	<!-- setup modal behaviour -->
	<BeamModal @confirmmodal="confirmModal" @closemodal="closeModal" :showModal="showModal">
		<Confirm @confirmmodal="confirmModal" @closemodal="closeModal" />
	</BeamModal>
	<BeamModalOutlet @confirmmodal="confirmModal" @closemodal="closeModal"></BeamModalOutlet>

	<!-- setup scan input listeners -->
	<ScanInput :scanHandler="scan" @scanInstance="registerInstance" />
	<Camera :allow-photo="allowPhoto" @scan="scan" @photos-captured="handlePhotosCaptured" />

	<!-- setup main view -->
	<RouterView />
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
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

// Route meta (including cameraPhoto) comes from hooks.py via yarn build.
// Prefer useRouter() here — pinia's markRaw(router) is for stores, not this component.
const allowPhoto = computed(() => Boolean(router.currentRoute.value.meta.cameraPhoto))

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
	--sc-input-active-border-color: #000000;
	--sc-input-border-color: #cccccc;
	--sc-row-color-zebra-light: #eeeeee;
}
</style>
