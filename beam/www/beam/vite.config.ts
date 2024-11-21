// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import vue from '@vitejs/plugin-vue'
import { resolve, dirname } from 'path'
import Components from 'unplugin-vue-components/vite'
import VueRouter from 'unplugin-vue-router/vite'
import { defineConfig } from 'vite'
import { readFileSync, existsSync } from 'fs'

import { getComponentPluginOptions } from './plugins/component.js'
import { getComponentPaths, getRoutes } from './plugins/router.js'

function findAppsRoot(startPath: string = __dirname): string {
	let currentPath = startPath
	let parentDir = dirname(currentPath)

	while (currentPath !== '/' && currentPath !== parentDir) {
		const dirName = currentPath.split('/').pop()
		if (dirName === 'apps' && existsSync(currentPath)) {
			return currentPath
		}

		currentPath = parentDir
		parentDir = dirname(currentPath)
	}

	throw new Error('Could not find "apps" directory in parent path')
}

function getBeamWebRoot() {
	const appsRoot = findAppsRoot()
	const beamWebPath = resolve(appsRoot, 'beam/beam/www/beam')

	if (!existsSync(beamWebPath)) {
		throw new Error(`Beam web directory not found at expected path: ${beamWebPath}`)
	}

	return beamWebPath
}

function getBeamNode() {
	const appsRoot = findAppsRoot()
	const beamWebPath = resolve(appsRoot, 'beam/node_modules')

	if (!existsSync(beamWebPath)) {
		throw new Error(`Beam web directory not found at expected path: ${beamWebPath}`)
	}

	return beamWebPath
}

export default defineConfig({
	plugins: [
		Components({ ...getComponentPluginOptions() }),
		VueRouter({
			routesFolder: resolve(__dirname, 'routes'),
			dts: 'beam/www/beam/typed-router.d.ts',

			beforeWriteFiles: root => {
				// remove all existing routes
				for (const child of root.children) {
					child.delete()
				}

				// add routes from all apps that have defined Beam routes
				const routes = getRoutes()
				const componentPaths = getComponentPaths()
				for (const route of routes) {
					if (componentPaths[route.component]) {
						const routeNode = root.insert(route.path, componentPaths[route.component])
						routeNode.name = route.name
						routeNode.addToMeta({ ...route.meta })
					}
				}
			},
		}),
		vue(),
	],
	resolve: {
		alias: {
			'@beam': getBeamWebRoot(),
			'@beamNode': getBeamNode(),
			'@': getBeamWebRoot(),
			'@/plugins': resolve(__dirname, 'plugins'),
			'@/types': resolve(__dirname, 'types'),
		},
	},

	build: {
		minify: false,
		emptyOutDir: false,
		sourcemap: 'inline',
		outDir: './beam/www/beam/',
		target: 'esnext',
		lib: {
			entry: resolve(__dirname, 'index.ts'),
			name: 'beam',
			formats: ['umd'], // only create module output for Frappe
			fileName: () => 'index.js',
		},
		rollupOptions: {
			output: {
				globals: {
					vue: 'Vue',
					'vue-router': 'VueRouter',
					pinia: 'Pinia',
					'@vueuse/core': 'VueUse',
					'@stonecrop/beam': 'Beam',
					'onscan.js': 'onScan',
					'vue-toast-notification': 'VueToast',
					typescript: 'ts',
				},
				assetFileNames: 'index.[ext]',
				extend: true,
				amd: {
					id: 'beam',
				},
				inlineDynamicImports: true,
			},
		},
	},

	define: {
		'process.env': process.env,
		__VUE_PROD_DEVTOOLS__: true,
	},
})
