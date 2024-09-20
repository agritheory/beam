// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'
import { resolve } from 'path'

export default defineConfig({
	server: {
		open: './dev.html',
	},
	plugins: [vue()],
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
			formats: ['es'], // only create module output for Frappe
			fileName: format => `index.js`, // creates module only output
		},
		rollupOptions: {
			output: {
				assetFileNames: 'index.[ext]',
			},
		},
	},
	define: {
		'process.env': process.env,
	},
})
