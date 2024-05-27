import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'
import { defineConfig } from 'vite'

export default defineConfig({
	plugins: [vue()],
	build: {
		lib: {
			entry: resolve(__dirname, 'beam.js'),
			name: 'beam',
			formats: ['es'], // creates module only output
			fileName: format => 'index.js',
			// TODO: need to figure out how to export index.css also
		},
		target: 'es2015',
		outDir: './',
		emptyOutDir: false,
		minify: false,
	},
	define: {
		'process.env': process.env,
	}
})
