<template>
	<div v-if="showComponent" class="camera-panel">
		<button
			type="button"
			class="camera-fab"
			:aria-label="isOpen ? 'Close camera' : 'Open camera'"
			:aria-expanded="isOpen"
			@click="toggleOpen">
			<svg class="camera-fab-icon" viewBox="0 0 24 24" aria-hidden="true">
				<path
					fill="currentColor"
					d="M9 2L7.17 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2h-3.17L15 2H9zm3 15c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.65 0-3 1.35-3 3s1.35 3 3 3 3-1.35 3-3-1.35-3-3-3z" />
			</svg>
		</button>

		<div v-if="isOpen" class="camera-backdrop" @click="closeCamera"></div>

		<div v-if="isOpen" class="camera-sheet" role="dialog" aria-label="Camera">
			<header class="camera-sheet-header">
				<div v-if="props.allowPhoto" class="camera-mode-toggle" role="tablist">
					<button
						type="button"
						role="tab"
						:aria-selected="mode === 'scan'"
						:class="{ active: mode === 'scan' }"
						@click="mode = 'scan'">
						Scan
					</button>
					<button
						type="button"
						role="tab"
						:aria-selected="mode === 'photo'"
						:class="{ active: mode === 'photo' }"
						@click="mode = 'photo'">
						Photo
					</button>
				</div>
				<span v-else class="camera-sheet-title">Scan barcode</span>
				<BeamBtn type="button" class="camera-close" aria-label="Close camera" @click="closeCamera"> Close </BeamBtn>
			</header>

			<div class="camera-preview" :class="{ 'camera-preview--photo': props.allowPhoto && mode === 'photo' }">
				<video ref="videoRef" autoplay muted playsinline class="camera-video"></video>
			</div>

			<div v-if="props.allowPhoto && mode === 'photo'" class="photo-controls">
				<button type="button" class="capture-btn" aria-label="Take photo" @click="capturePhoto">
					<span class="capture-circle"></span>
				</button>
				<BeamBtn type="button" class="attach-btn" :disabled="capturedPhotos.length === 0" @click="attachPhotos">
					Attach{{ capturedPhotos.length ? ` (${capturedPhotos.length})` : '' }}
				</BeamBtn>
			</div>

			<div v-if="props.allowPhoto && props.allowPreview && capturedPhotos.length > 0" class="photos-preview">
				<div v-for="(photo, index) in capturedPhotos" :key="index" class="photo-item">
					<img :src="photo.preview" alt="Captured photo" />
					<button type="button" class="remove-photo" aria-label="Remove photo" @click="removePhoto(index)">✕</button>
				</div>
			</div>

			<div v-if="errorMessage" class="error-message" role="alert">
				<p>
					<strong>{{ errorMessage }}</strong>
				</p>
				<div v-if="showPermissionHelp">
					<p>You must allow camera access in your browser settings.</p>
					<p><small>On mobile devices, check the permissions in Settings → Apps → Browser</small></p>
				</div>
			</div>
		</div>

		<canvas ref="canvasRef" class="camera-canvas"></canvas>
	</div>
</template>

<script setup lang="ts">
import { ref, onUnmounted, onMounted, nextTick } from 'vue'
import { Html5Qrcode } from 'html5-qrcode'
import { BarcodeDetector, prepareZXingModule, type BarcodeFormat } from 'barcode-detector/ponyfill'
import zxingReaderWasmUrl from 'zxing-wasm/reader/zxing_reader.wasm?url'

interface CapturedPhoto {
	file: File
	preview: string
}

// Do not destructure — loses reactivity when parent allowPhoto flips with the route.
const props = withDefaults(
	defineProps<{
		allowPhoto?: boolean
		allowPreview?: boolean
	}>(),
	{
		allowPhoto: false,
		allowPreview: true,
	}
)

const emit = defineEmits<{
	scan: [barcode: string, qty: number]
	photosCaptured: [files: File[]]
}>()

const isOpen = ref(false)
const mode = ref<'scan' | 'photo'>('scan')
const showComponent = ref(true)
const errorMessage = ref('')
const showPermissionHelp = ref(false)
const videoRef = ref<HTMLVideoElement | null>(null)
const canvasRef = ref<HTMLCanvasElement | null>(null)
const capturedPhotos = ref<CapturedPhoto[]>([])

let mediaStream: MediaStream | null = null
let nativeScanTimer: ReturnType<typeof setInterval> | null = null
let nativeScanInFlight = false
let nativeScanTick = 0
let lastEmittedBarcode = ''
let lastEmittedAt = 0

const PREVIEW_HEIGHT_PX = 150
const NATIVE_DECODE_SCALE = 2

let wasmInitError = 'none'
let wasmBarcodeDetector: BarcodeDetector | null = null

const barcodeDetectorFormats: BarcodeFormat[] = ['upc_a', 'upc_e', 'ean_13', 'ean_8', 'code_128', 'code_39']

const formatDecodeError = (err: unknown): string => {
	if (err && typeof err === 'object') {
		const errorObject = err as { kind?: string; name?: string; message?: string }
		return errorObject.kind || errorObject.name || errorObject.message || String(err).slice(0, 120)
	}
	return String(err).slice(0, 120)
}

const isMobileDevice = () => /iPhone|iPad|iPod|Android/i.test(navigator.userAgent)

const initWasmBarcodeDetector = async () => {
	wasmBarcodeDetector = null
	wasmInitError = 'none'

	try {
		await prepareZXingModule({
			overrides: {
				locateFile: (path, prefix) => {
					if (path.endsWith('.wasm')) {
						return zxingReaderWasmUrl
					}
					return prefix + path
				},
			},
		})
		wasmBarcodeDetector = new BarcodeDetector({ formats: barcodeDetectorFormats })
	} catch (err) {
		wasmInitError = formatDecodeError(err)
	}
}

const checkCameraPermissions = async () => {
	try {
		if (!window.isSecureContext) {
			showComponent.value = false
			return
		}

		if (!navigator.mediaDevices?.getUserMedia) {
			showComponent.value = false
			return
		}
	} catch {
		showComponent.value = false
	}
}

type CameraConstraintPlan = {
	label: string
	constraints: MediaStreamConstraints
}

const buildCameraConstraintPlans = async (): Promise<CameraConstraintPlan[]> => {
	const plans: CameraConstraintPlan[] = []

	try {
		const cameras = await Html5Qrcode.getCameras()
		if (cameras.length > 0) {
			const rearCamera = cameras.find(camera => /back|rear|environment/i.test(camera.label))
			const preferred = rearCamera || cameras[0]
			plans.push({
				label: preferred.label || preferred.id,
				constraints: {
					audio: false,
					video: {
						deviceId: { exact: preferred.id },
						width: { ideal: 1280 },
						height: { ideal: 720 },
					},
				},
			})

			for (const camera of cameras) {
				if (camera.id === preferred.id) {
					continue
				}
				plans.push({
					label: camera.label || camera.id,
					constraints: {
						audio: false,
						video: {
							deviceId: { exact: camera.id },
							width: { ideal: 1280 },
							height: { ideal: 720 },
						},
					},
				})
			}
		}
	} catch {
		// fall through to facingMode plans
	}

	if (isMobileDevice()) {
		plans.push({
			label: 'environment',
			constraints: {
				audio: false,
				video: {
					facingMode: { ideal: 'environment' },
					width: { ideal: 1280 },
					height: { ideal: 720 },
				},
			},
		})
	}

	plans.push({
		label: 'user',
		constraints: {
			audio: false,
			video: {
				facingMode: 'user',
				width: { ideal: 1280 },
				height: { ideal: 720 },
			},
		},
	})

	return plans
}

const formatStartError = (err: any) => {
	if (err?.name === 'NotAllowedError' || err?.name === 'PermissionDeniedError') {
		showPermissionHelp.value = true
		return 'Permission denied to access camera'
	}
	if (err?.name === 'NotFoundError' || err?.name === 'DevicesNotFoundError') {
		return 'There is no camera found on this device'
	}
	return err?.message || String(err)
}

const waitForVideoDimensions = (video: HTMLVideoElement) =>
	new Promise<void>((resolve, reject) => {
		const deadline = Date.now() + 5000
		const check = () => {
			if (video.videoWidth > 0 && video.videoHeight > 0) {
				resolve()
				return
			}
			if (Date.now() > deadline) {
				reject(new Error('Camera video did not become ready'))
				return
			}
			requestAnimationFrame(check)
		}
		check()
	})

const getVideoElement = () => videoRef.value

const onScanSuccess = (decodedText: string) => {
	const barcode = decodedText.trim()
	if (!barcode) {
		return
	}

	const now = Date.now()
	if (barcode === lastEmittedBarcode && now - lastEmittedAt < 1500) {
		return
	}

	lastEmittedBarcode = barcode
	lastEmittedAt = now
	emit('scan', barcode, 1)
}

const captureFullFrameCanvas = (): HTMLCanvasElement | null => {
	const videoElement = getVideoElement()
	if (!videoElement || videoElement.readyState < HTMLMediaElement.HAVE_ENOUGH_DATA) {
		return null
	}
	if (!videoElement.videoWidth || !videoElement.videoHeight) {
		return null
	}

	const canvas = document.createElement('canvas')
	canvas.width = Math.round(videoElement.videoWidth * NATIVE_DECODE_SCALE)
	canvas.height = Math.round(videoElement.videoHeight * NATIVE_DECODE_SCALE)
	const context = canvas.getContext('2d', { willReadFrequently: true })
	if (!context) {
		return null
	}

	context.drawImage(videoElement, 0, 0, canvas.width, canvas.height)
	return canvas
}

const captureCenterCropCanvas = (): HTMLCanvasElement | null => {
	const videoElement = getVideoElement()
	if (!videoElement || videoElement.readyState < HTMLMediaElement.HAVE_ENOUGH_DATA) {
		return null
	}
	if (!videoElement.videoWidth || !videoElement.videoHeight) {
		return null
	}

	const cropWidth = Math.floor(videoElement.videoWidth * 0.75)
	const cropHeight = Math.floor(videoElement.videoHeight * 0.45)
	const sx = Math.floor((videoElement.videoWidth - cropWidth) / 2)
	const sy = Math.floor((videoElement.videoHeight - cropHeight) / 2)

	const canvas = document.createElement('canvas')
	canvas.width = Math.round(cropWidth * NATIVE_DECODE_SCALE)
	canvas.height = Math.round(cropHeight * NATIVE_DECODE_SCALE)
	const context = canvas.getContext('2d', { willReadFrequently: true })
	if (!context) {
		return null
	}

	context.drawImage(videoElement, sx, sy, cropWidth, cropHeight, 0, 0, canvas.width, canvas.height)
	return canvas
}

const captureVisibleStripCanvas = (): HTMLCanvasElement | null => {
	const videoElement = getVideoElement()
	if (!videoElement) {
		return null
	}
	if (videoElement.readyState < HTMLMediaElement.HAVE_ENOUGH_DATA) {
		return null
	}
	if (!videoElement.videoWidth || !videoElement.videoHeight || !videoElement.clientWidth) {
		return null
	}

	const heightRatio = videoElement.videoHeight / videoElement.clientHeight
	const nativeStripHeight = Math.min(PREVIEW_HEIGHT_PX * heightRatio, videoElement.videoHeight)
	const nativeStripWidth = videoElement.videoWidth

	const canvas = document.createElement('canvas')
	canvas.width = Math.round(nativeStripWidth * NATIVE_DECODE_SCALE)
	canvas.height = Math.round(nativeStripHeight * NATIVE_DECODE_SCALE)
	const context = canvas.getContext('2d', { willReadFrequently: true })
	if (!context) {
		return null
	}

	context.drawImage(videoElement, 0, 0, nativeStripWidth, nativeStripHeight, 0, 0, canvas.width, canvas.height)

	return canvas
}

const flipCanvasHorizontally = (source: HTMLCanvasElement): HTMLCanvasElement => {
	const flipped = document.createElement('canvas')
	flipped.width = source.width
	flipped.height = source.height
	const context = flipped.getContext('2d', { willReadFrequently: true })
	if (!context) {
		return source
	}
	context.translate(flipped.width, 0)
	context.scale(-1, 1)
	context.drawImage(source, 0, 0)
	return flipped
}

const decodeWithWasmBarcodeDetector = async (canvas: HTMLCanvasElement): Promise<string | null> => {
	if (!wasmBarcodeDetector) {
		return null
	}

	try {
		const results = await wasmBarcodeDetector.detect(canvas)
		return results[0]?.rawValue ?? null
	} catch {
		return null
	}
}

const tryDecodeCanvas = async (canvas: HTMLCanvasElement): Promise<string | null> => {
	for (const flip of [false, true]) {
		const attemptCanvas = flip ? flipCanvasHorizontally(canvas) : canvas
		const decodedText = await decodeWithWasmBarcodeDetector(attemptCanvas)
		if (decodedText) {
			return decodedText
		}
	}

	return null
}

const captureForTick = (): HTMLCanvasElement | null => {
	const planIndex = nativeScanTick % 3
	if (planIndex === 1) {
		return captureFullFrameCanvas()
	}
	if (planIndex === 2) {
		return captureCenterCropCanvas()
	}
	return captureVisibleStripCanvas()
}

const decodeCurrentFrame = async (): Promise<string | null> => {
	const canvas = captureForTick()
	if (!canvas) {
		return null
	}
	return tryDecodeCanvas(canvas)
}

const startNativeScanLoop = () => {
	nativeScanTick = 0
	nativeScanTimer = setInterval(async () => {
		if (nativeScanInFlight) {
			return
		}

		nativeScanInFlight = true
		nativeScanTick += 1

		try {
			const decodedText = await decodeCurrentFrame()
			if (decodedText) {
				onScanSuccess(decodedText)
			}
		} finally {
			nativeScanInFlight = false
		}
	}, 150)
}

const openCameraStream = async (): Promise<MediaStream> => {
	const plans = await buildCameraConstraintPlans()
	let lastError: any = null

	for (const plan of plans) {
		try {
			return await navigator.mediaDevices.getUserMedia(plan.constraints)
		} catch (err) {
			lastError = err
		}
	}

	throw lastError || new Error('Unable to open camera')
}

const attachStream = async (stream: MediaStream) => {
	const video = videoRef.value
	if (!video) {
		throw new Error('Camera preview element not found')
	}

	video.srcObject = stream
	await video.play()
	await waitForVideoDimensions(video)
}

const emitCapturedPhotos = () => {
	emit(
		'photosCaptured',
		capturedPhotos.value.map(photo => photo.file)
	)
}

const capturePhoto = () => {
	const video = videoRef.value
	const canvas = canvasRef.value
	if (!video || !canvas) {
		return
	}

	canvas.width = video.videoWidth
	canvas.height = video.videoHeight

	const context = canvas.getContext('2d')
	if (!context) {
		return
	}

	context.drawImage(video, 0, 0, canvas.width, canvas.height)

	canvas.toBlob(
		blob => {
			if (!blob) {
				return
			}

			const timestamp = Date.now()
			const fileName = `photo_${timestamp}.jpg`
			const file = new File([blob], fileName, {
				type: 'image/jpeg',
				lastModified: timestamp,
			})
			const preview = URL.createObjectURL(blob)

			capturedPhotos.value.push({ file, preview })
			emitCapturedPhotos()
		},
		'image/jpeg',
		0.95
	)
}

const removePhoto = (index: number) => {
	URL.revokeObjectURL(capturedPhotos.value[index].preview)
	capturedPhotos.value.splice(index, 1)
	emitCapturedPhotos()
}

const attachPhotos = () => {
	emitCapturedPhotos()
	closeCamera()
}

const startCamera = async () => {
	errorMessage.value = ''
	showPermissionHelp.value = false
	lastEmittedBarcode = ''
	lastEmittedAt = 0
	mode.value = 'scan'

	await nextTick()

	try {
		await initWasmBarcodeDetector()
		if (!wasmBarcodeDetector) {
			throw new Error(wasmInitError || 'Barcode scanner failed to initialize')
		}

		mediaStream = await openCameraStream()
		await attachStream(mediaStream)
		startNativeScanLoop()
	} catch (err) {
		errorMessage.value = formatStartError(err)
		stopCamera()
	}
}

const stopCamera = () => {
	if (nativeScanTimer) {
		clearInterval(nativeScanTimer)
		nativeScanTimer = null
	}

	if (mediaStream) {
		for (const track of mediaStream.getTracks()) {
			track.stop()
		}
		mediaStream = null
	}

	if (videoRef.value) {
		videoRef.value.srcObject = null
	}
}

const openCamera = async () => {
	isOpen.value = true
	await startCamera()
}

const closeCamera = () => {
	stopCamera()
	isOpen.value = false
	errorMessage.value = ''
	showPermissionHelp.value = false
}

const toggleOpen = async () => {
	if (!isOpen.value) {
		await openCamera()
	} else {
		closeCamera()
	}
}

onMounted(async () => {
	await checkCameraPermissions()
})

onUnmounted(() => {
	stopCamera()
	capturedPhotos.value.forEach(photo => URL.revokeObjectURL(photo.preview))
})
</script>

<style scoped>
/* Stonecrop UI: gray-on-gray default, low radius, theme tokens, modal z-index 200–299 */

.camera-fab {
	position: fixed;
	left: 1rem;
	right: auto;
	bottom: calc(5.5rem + env(safe-area-inset-bottom, 0px));
	z-index: 150; /* floating control */
	width: 3rem;
	height: 3rem;
	border: 1px solid var(--sc-btn-border);
	border-radius: 0;
	background: var(--sc-btn-color);
	color: var(--sc-btn-label-color);
	display: flex;
	align-items: center;
	justify-content: center;
	cursor: pointer;
	font-family: var(--sc-font-family);
}

.camera-fab:hover,
.camera-fab:active {
	background: var(--sc-btn-hover);
}

.camera-fab-icon {
	width: 1.5rem;
	height: 1.5rem;
}

.camera-backdrop {
	position: fixed;
	inset: 0;
	z-index: 250; /* modal tier */
	background: rgba(51, 51, 51, 0.45);
	backdrop-filter: blur(2px);
}

.camera-sheet {
	position: fixed;
	left: 0;
	right: 0;
	bottom: 0;
	z-index: 251;
	max-height: 90vh;
	display: flex;
	flex-direction: column;
	background: var(--sc-form-background, #ffffff);
	border-radius: 0;
	border-top: 1px solid var(--sc-row-border-color, var(--sc-gray-20));
	overflow: hidden;
	font-family: var(--sc-font-family);
	color: var(--sc-cell-text-color, var(--sc-gray-80));
}

.camera-sheet-header {
	display: flex;
	align-items: center;
	justify-content: space-between;
	gap: 0.75rem;
	padding: 0.625rem;
	background: var(--sc-gray-5);
	border-bottom: 1px solid var(--sc-row-border-color, var(--sc-gray-20));
}

.camera-sheet-title {
	font-weight: 600;
	font-size: 1rem;
	color: var(--sc-gray-80);
}

.camera-mode-toggle {
	display: flex;
	border: 1px solid var(--sc-btn-border);
	background: var(--sc-btn-color);
}

.camera-mode-toggle button {
	border: none;
	border-right: 1px solid var(--sc-btn-border);
	background: transparent;
	color: var(--sc-btn-label-color);
	padding: 0.375rem 0.875rem;
	border-radius: 0;
	font-weight: 600;
	font-family: var(--sc-font-family);
	font-size: 0.875rem;
	cursor: pointer;
}

.camera-mode-toggle button:last-child {
	border-right: none;
}

.camera-mode-toggle button.active {
	background: var(--sc-primary-color);
	color: var(--sc-primary-text-color);
}

.camera-mode-toggle button:hover:not(.active) {
	background: var(--sc-btn-hover);
}

.camera-close {
	flex-shrink: 0;
}

.camera-preview {
	height: 150px;
	overflow: hidden;
	background: var(--sc-gray-80);
	border-top: 1px solid var(--sc-row-border-color, var(--sc-gray-20));
	border-bottom: 1px solid var(--sc-row-border-color, var(--sc-gray-20));
}

.camera-preview--photo {
	height: min(45vh, 360px);
}

.camera-video {
	width: 100%;
	display: block;
}

.photo-controls {
	display: flex;
	flex-direction: column;
	align-items: center;
	gap: 0.75rem;
	padding: 1rem 0.625rem;
	background: var(--sc-gray-5);
}

.capture-btn {
	background: var(--sc-btn-color);
	border: 2px solid var(--sc-primary-color);
	border-radius: 0;
	width: 4rem;
	height: 4rem;
	display: flex;
	align-items: center;
	justify-content: center;
	cursor: pointer;
	padding: 0;
}

.capture-btn:hover,
.capture-btn:active {
	background: var(--sc-btn-hover);
}

.capture-circle {
	width: 2.5rem;
	height: 2.5rem;
	background: var(--sc-primary-color);
	border-radius: 0;
}

.attach-btn {
	width: 100%;
	max-width: 20rem;
	padding: 0.625rem 0.75rem !important;
	background-color: var(--sc-primary-color) !important;
	color: var(--sc-primary-text-color) !important;
	border-color: var(--sc-primary-color) !important;
	font-weight: 700;
	letter-spacing: 0.04em;
}

.attach-btn:disabled {
	opacity: 0.45;
	cursor: not-allowed;
}

.photos-preview {
	display: grid;
	grid-template-columns: repeat(auto-fill, minmax(100px, 1fr));
	gap: 0.5rem;
	padding: 0.625rem;
	background: var(--sc-form-background, #ffffff);
	border-top: 1px solid var(--sc-row-border-color, var(--sc-gray-20));
	max-height: 140px;
	overflow-y: auto;
}

.photo-item {
	position: relative;
	border: 1px solid var(--sc-input-border-color, var(--sc-gray-20));
	border-radius: 0;
	overflow: hidden;
	background: var(--sc-gray-10);
}

.photo-item img {
	width: 100%;
	height: 80px;
	object-fit: cover;
	display: block;
}

.remove-photo {
	position: absolute;
	top: 0;
	right: 0;
	background: var(--sc-brand-danger);
	color: var(--sc-primary-text-color);
	border: none;
	border-radius: 0;
	width: 1.5rem;
	height: 1.5rem;
	font-size: 0.875rem;
	line-height: 1;
	cursor: pointer;
	font-family: var(--sc-font-family);
}

.camera-canvas {
	display: none;
}

.error-message {
	color: var(--sc-brand-danger);
	text-align: left;
	padding: 0.625rem;
	background: var(--sc-gray-5);
	border-top: 1px solid var(--sc-brand-danger);
	font-family: var(--sc-font-family);
}

.error-message strong {
	display: block;
	margin-bottom: 0.5rem;
}
</style>
