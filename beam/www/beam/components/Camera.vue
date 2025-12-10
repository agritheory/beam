<template>
	<div v-if="showComponent" class="camera-component">
		<button @click="toggleCamera" class="camera-btn">
			<span v-if="!isOpen">Take photo</span>
			<span v-else>Close</span>
		</button>

		<div v-if="allowPreview && capturedPhotos.length > 0" class="photos-preview">
			<div v-for="(photo, index) in capturedPhotos" :key="index" class="photo-item">
				<img :src="photo.preview" alt="Captured photo" />
				<button @click="removePhoto(index)" class="remove-photo">✕</button>
			</div>
		</div>

		<!-- Camera -->
		<div v-if="isOpen" class="camera-container">
			<video ref="videoElement" autoplay playsinline class="camera-video"></video>
			<canvas ref="canvasElement" class="camera-canvas"></canvas>

			<div class="camera-controls">
				<button @click="capturePhoto" class="capture-btn">
					<span class="capture-circle"></span>
				</button>
			</div>
		</div>

		<div v-if="errorMessage" class="error-message">
			<p>
				<strong>{{ errorMessage }}</strong>
			</p>
		</div>
	</div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'

interface CapturedPhoto {
	file: File
	preview: string
}
const { allowPreview = true } = defineProps<{ allowPreview: Boolean }>()

const emit = defineEmits<{
	photosCaptured: [files: File[]]
}>()

const isOpen = ref(false)
const showComponent = ref(true)
const videoElement = ref<HTMLVideoElement | null>(null)
const canvasElement = ref<HTMLCanvasElement | null>(null)
const errorMessage = ref<string>('')
const capturedPhotos = ref<CapturedPhoto[]>([])
let stream: MediaStream | null = null

const toggleCamera = async () => {
	if (!isOpen.value) {
		await startCamera()
	} else {
		stopCamera()
	}
}

const startCamera = async () => {
	errorMessage.value = ''

	try {
		if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
			showComponent.value = false
			return
		}

		stream = await navigator.mediaDevices.getUserMedia({
			video: { facingMode: 'environment' },
			audio: false,
		})

		isOpen.value = true

		await new Promise(resolve => setTimeout(resolve, 100))

		if (videoElement.value) {
			videoElement.value.srcObject = stream
		}
	} catch (err: any) {
		isOpen.value = false

		if (err.name === 'NotAllowedError' || err.name === 'PermissionDeniedError') {
			errorMessage.value = 'Permission denied to access camera'
		} else if (err.name === 'NotFoundError' || err.name === 'DevicesNotFoundError') {
			errorMessage.value = 'There is no camera found on this device'
		} else {
			errorMessage.value = err.message || err.toString()
		}
	}
}

const stopCamera = () => {
	if (stream) {
		stream.getTracks().forEach(track => track.stop())
		stream = null
	}
	isOpen.value = false
}

const capturePhoto = () => {
	if (!videoElement.value || !canvasElement.value) return

	const video = videoElement.value
	const canvas = canvasElement.value

	canvas.width = video.videoWidth
	canvas.height = video.videoHeight

	const ctx = canvas.getContext('2d')
	if (!ctx) return

	ctx.drawImage(video, 0, 0, canvas.width, canvas.height)

	canvas.toBlob(
		blob => {
			if (!blob) return

			const timestamp = new Date().getTime()
			const fileName = `photo_${timestamp}.jpg`

			const file = new File([blob], fileName, {
				type: 'image/jpeg',
				lastModified: timestamp,
			})

			const preview = URL.createObjectURL(blob)

			capturedPhotos.value.push({ file, preview })

			emit(
				'photosCaptured',
				capturedPhotos.value.map(p => p.file)
			)

			stopCamera()
		},
		'image/jpeg',
		0.95
	)
}

const removePhoto = (index: number) => {
	URL.revokeObjectURL(capturedPhotos.value[index].preview)

	capturedPhotos.value.splice(index, 1)

	emit(
		'photosCaptured',
		capturedPhotos.value.map(p => p.file)
	)
}

onMounted(() => {
	if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
		showComponent.value = false
	}
})

onUnmounted(() => {
	stopCamera()
	capturedPhotos.value.forEach(photo => URL.revokeObjectURL(photo.preview))
})
</script>

<style scoped>
.camera-component {
	margin: 1rem 0;
}

@media (min-width: 769px) {
	.camera-component {
		display: none;
	}
}

.camera-btn {
	display: flex;
	align-items: center;
	gap: 0.5rem;
	padding: 0.75rem 1rem;
	background: #42b883;
	color: white;
	border: none;
	border-radius: 2px;
}

.camera-icon {
	width: 24px;
	height: 24px;
}

.photos-preview {
	display: grid;
	grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
	gap: 1rem;
	margin-top: 1rem;
}

.photo-item {
	position: relative;
	border: 2px solid #42b883;
	border-radius: 8px;
	overflow: hidden;
}

.photo-item img {
	width: 100%;
	height: 150px;
	object-fit: cover;
	display: block;
}

.remove-photo {
	position: absolute;
	top: 5px;
	right: 5px;
	background: rgba(255, 0, 0, 0.8);
	color: white;
	border: none;
	border-radius: 50%;
	width: 30px;
	height: 30px;
	font-size: 18px;
	cursor: pointer;
	display: flex;
	align-items: center;
	justify-content: center;
}

.camera-container {
	position: relative;
	margin-top: 1rem;
	background: #000;
	border-radius: 8px;
	overflow: hidden;
	max-width: 600px;
	margin-left: auto;
	margin-right: auto;
}

.camera-video {
	width: 100%;
	height: 400px;
	object-fit: cover;
	display: block;
}

.camera-canvas {
	display: none;
}

.camera-controls {
	position: absolute;
	bottom: 20px;
	left: 50%;
	transform: translateX(-50%);
	z-index: 10;
}

.capture-btn {
	background: white;
	border: 4px solid #42b883;
	border-radius: 50%;
	width: 70px;
	height: 70px;
	display: flex;
	align-items: center;
	justify-content: center;
	cursor: pointer;
	transition: transform 0.1s;
}

.capture-btn:active {
	transform: scale(0.95);
}

.capture-circle {
	width: 50px;
	height: 50px;
	background: #42b883;
	border-radius: 50%;
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
