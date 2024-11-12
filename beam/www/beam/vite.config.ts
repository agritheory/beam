// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'
import Components from 'unplugin-vue-components/vite'
import VueRouter from 'unplugin-vue-router/vite'
import { defineConfig } from 'vite'

import { getComponentPluginOptions } from './plugins/component.js'
import { getComponentPaths, getRoutes } from './plugins/router.js'

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
			'@': resolve(__dirname),
			'@/plugins': resolve(__dirname, 'plugins'),
			'@/types': resolve(__dirname, 'types'),
		},
	},

	build: {
		emptyOutDir: false,
		sourcemap: true,
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
				assetFileNames: 'index.[ext]',
			},
		},
	},

	define: {
		'process.env': process.env,
		__VUE_PROD_DEVTOOLS__: true,
	},
})
