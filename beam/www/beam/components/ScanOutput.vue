<template>
	<SplitColumn v-if="store.scanner.lastScan" class="scan-output">
		<template #right>
			<BeamHeading>
				<span class="beam--normal">{{ store.scanner.lastDocType }}</span>
			</BeamHeading>
		</template>
		<template #left>
			<output>{{ store.scanner.lastScan }}</output>
		</template>
	</SplitColumn>
</template>

<script setup lang="ts">
import { SplitColumn } from '@stonecrop/beam'
import { useBeamStore } from '@/stores/beam'

const store = useBeamStore()
</script>

<style>
.scan-output {
	background-color: var(--sc-primary-color);
	margin-left: 0;
	min-height: 2em;
	max-height: 2em;
	color: var(--sc-primary-text-color);
	width: 100%;
}

.scan-output output {
	width: calc(50% - 2px);
	padding-left: 2em;
	padding-right: 2em;
	text-align: right;
	color: var(--sc-alert);
	font-family: monospace, monospace !important;
	font-size: 18px;
}
</style>
