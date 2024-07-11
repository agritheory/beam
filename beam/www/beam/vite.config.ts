import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'
import { resolve } from 'path'


export default defineConfig({
	plugins: [vue()],
	build: {
		target: 'esnext',
		sourcemap: true,
		root: './',
		outDir: './beam/www/beam/',
		emptyOutDir: false,
		minify: false,
		lib: {
			entry: resolve(__dirname, 'index.ts'),
			name: 'beam',
			formats: ['es'], // only create module output for Frappe
			fileName: format => `index.js`, // creates module only output
		},
	},
	define: {
		'process.env': process.env,
	},
})