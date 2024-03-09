import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { VitePWA } from 'vite-plugin-pwa'
import path from 'path'

export default defineConfig({
	plugins: [
		vue(),
		// VitePWA({
		// 	registerType: "autoUpdate",
		// 	devOptions: {
		// 		enabled: true,
		// 	},
		// 	manifest: {
		// 		display: "standalone",
		// 		name: "Frappe HR",
		// 		short_name: "Frappe HR",
		// 		start_url: "/hrms",
		// 		description: "Everyday HR & Payroll operations at your fingertips",
		// 		icons: [
		// 			{
		// 				src: "/assets/hrms/manifest/manifest-icon-192.maskable.png",
		// 				sizes: "192x192",
		// 				type: "image/png",
		// 				purpose: "any",
		// 			},
		// 			{
		// 				src: "/assets/hrms/manifest/manifest-icon-192.maskable.png",
		// 				sizes: "192x192",
		// 				type: "image/png",
		// 				purpose: "maskable",
		// 			},
		// 			{
		// 				src: "/assets/hrms/manifest/manifest-icon-512.maskable.png",
		// 				sizes: "512x512",
		// 				type: "image/png",
		// 				purpose: "any",
		// 			},
		// 			{
		// 				src: "/assets/hrms/manifest/manifest-icon-512.maskable.png",
		// 				sizes: "512x512",
		// 				type: "image/png",
		// 				purpose: "maskable",
		// 			},
		// 		],
		// 	},
		// }),
	],
	build: {
		lib: {
			entry: path.resolve(__dirname, 'beam.js'),
			name: 'timeclock',
			fileName: format => `index.js`, // creates module only output
			// TODO: need to figure out how to export index.css also
		},
		outDir: './beam/www/beam/',
		root: './',
		target: 'es2015',
		emptyOutDir: false,
		minify: false,
	},
	optimizeDeps: {},
	define: {
		'process.env': process.env,
	},
})
