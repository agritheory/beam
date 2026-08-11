<template>
	<div v-if="showComponent" class="camera-scanner">
		<BeamBtn @click="toggleCamera" :disabled="!canUseCamera">
			<span v-if="!isScanning">Open Camera</span>
			<span v-else>Close</span>
		</BeamBtn>

		<div v-if="isScanning" class="scanner-container">
			<div id="camera-reader"></div>
			<p v-if="lastScanned" class="last-scan">Last scanned: {{ lastScanned }}</p>
		</div>

		<div v-if="errorMessage" class="error-message">
			<p>
				<strong>{{ errorMessage }}</strong>
			</p>
			<div v-if="showPermissionHelp">
				<p>You must allow camera access in your browser settings.</p>
				<p><small>On mobile devices, check the permissions in Settings → Apps → Browser</small></p>
			</div>
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref, onUnmounted, computed, onMounted } from 'vue'
import { Html5Qrcode, Html5QrcodeSupportedFormats } from 'html5-qrcode'

const emit = defineEmits<{
	scan: [barcode: string, qty: number]
}>()

const isScanning = ref(false)
const showComponent = ref(true)
const lastScanned = ref<string>('')
const errorMessage = ref<string>('')
const showPermissionHelp = ref(false)
const hasCheckedPermissions = ref(false)
let html5QrCode: Html5Qrcode | null = null

const canUseCamera = computed(() => {
	return !errorMessage.value || isScanning.value
})

const checkCameraPermissions = async () => {
	try {
		if (!window.isSecureContext) {
			errorMessage.value = 'Camera access requires HTTPS'
			showComponent.value = false
			return
		}

		if (!navigator.mediaDevices?.getUserMedia) {
			errorMessage.value = 'Your browser does not support camera access'
			showComponent.value = false
			return
		}

		// Do not rely on enumerateDevices() to decide visibility. Browsers (especially
		// iOS Safari) often omit videoinput devices until after camera permission is granted.
		hasCheckedPermissions.value = true
		errorMessage.value = ''
	} catch (err) {
		errorMessage.value = err.message || err.toString()
	}
}

const startScanning = async () => {
	errorMessage.value = ''
	showPermissionHelp.value = false
	isScanning.value = true

	try {
		await new Promise(resolve => setTimeout(resolve, 100))

		try {
			const stream = await navigator.mediaDevices.getUserMedia({
				video: { facingMode: 'environment' },
			})
			stream.getTracks().forEach(track => track.stop())
		} catch (err: any) {
			isScanning.value = false

			if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
				errorMessage.value = 'Permission denied to access camera'
				showPermissionHelp.value = true
			} else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
				errorMessage.value = 'There is no camera found on this device'
			} else {
				errorMessage.value = err.message || err.toString()
			}
			return
		}

		html5QrCode = new Html5Qrcode('camera-reader', {
			formatsToSupport: [
				Html5QrcodeSupportedFormats.CODE_128,
				Html5QrcodeSupportedFormats.CODE_39,
				Html5QrcodeSupportedFormats.EAN_13,
				Html5QrcodeSupportedFormats.EAN_8,
				Html5QrcodeSupportedFormats.UPC_A,
				Html5QrcodeSupportedFormats.UPC_E,
			],
			verbose: false,
		})

		const config = {
			fps: 1,
			qrbox: { width: 280, height: 280 },
			aspectRatio: 1.0,
		}

		const cameraConfig = { facingMode: 'environment' }

		await html5QrCode.start(
			cameraConfig,
			config,
			decodedText => {
				lastScanned.value = decodedText
				emit('scan', decodedText, 1)
			},
			() => {
				// Error callback
			}
		)
	} catch (err: any) {
		isScanning.value = false
		errorMessage.value = err.message || err.toString()
	}
}

const stopScanning = async () => {
	if (html5QrCode && isScanning.value) {
		try {
			await html5QrCode.stop()
			html5QrCode.clear()
			isScanning.value = false
			lastScanned.value = ''
		} catch (err) {
			errorMessage.value = err.message || err.toString()
		}
	}
}

const toggleCamera = async () => {
	if (!isScanning.value) {
		await startScanning()
	} else {
		await stopScanning()
	}
}

onMounted(async () => {
	await checkCameraPermissions()
})

onUnmounted(() => {
	if (isScanning.value) {
		stopScanning()
	}
})
</script>

<style scoped>
.camera-scanner {
	margin: 1rem 0;
}

.scanner-container {
	background: #000;
	border-radius: 8px;
	padding: 1rem;
	margin-top: 1rem;
	max-width: 600px;
	margin-left: auto;
	margin-right: auto;
}

#camera-reader {
	width: 100%;
	height: 150px;
	position: relative;
	border: 2px solid #42b983;
	border-radius: 4px;
	overflow: hidden;
}

.last-scan {
	color: #42b983;
	text-align: center;
	margin-top: 0.5rem;
	font-weight: bold;
	font-size: 1rem;
}

.error-message {
	color: #721c24;
	text-align: left;
	padding: 1rem;
	background: #f8d7da;
	border: 1px solid #f5c6cb;
	border-radius: 4px;
	margin-top: 0.5rem;
}

.error-message strong {
	display: block;
	margin-bottom: 0.5rem;
}
</style>
