// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'
import Components from 'unplugin-vue-components/vite'
import VueRouter from 'unplugin-vue-router/vite'
import { defineConfig } from 'vite'
import { routes } from './routes'

import { BEAMResolver, RouteResolver } from './component_resolver.js'

export default defineConfig({
	plugins: [
		Components({ resolvers: [BEAMResolver()] }),
		VueRouter({
			beforeWriteFiles(root) {},
		}),
		vue(),
	],
	resolve: {
		alias: {
			'@': resolve(__dirname),
		},
	},
	build: {
		emptyOutDir: false,
		outDir: './beam/www/beam/',
		sourcemap: true,
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
