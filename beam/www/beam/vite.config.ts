import vue from '@vitejs/plugin-vue'
import { existsSync, readFileSync } from 'fs'
import { join, resolve } from 'path'
import { ServerOptions, defineConfig } from 'vite'

export default defineConfig({
	server: {
		open: './dev.html',
		proxy: getProxyOptions(),
	},
	plugins: [vue()],
	build: {
		target: 'esnext',
		outDir: resolve(__dirname, '..', '..', 'public/dist/js/portal/'),
		lib: {
			entry: resolve(__dirname, 'index.ts'),
			name: 'beam',
			formats: ['es'], // only create module output for Frappe
			// TODO: need to figure out how to export index.css also
		},
	},
	define: {
		'import.meta.env.FRAPPE_DEV_MODE': isDeveloperMode(),
		'process.env': process.env,
	},
})

function isDeveloperMode() {
	const config = getCommonSiteConfig()
	return Boolean(config?.developer_mode)
}

function getProxyOptions(): ServerOptions['proxy'] {
	const config = getCommonSiteConfig()
	const webserver_port = config ? config.webserver_port : 8000
	if (!config) {
		console.log('No common_site_config.json found, using default port 8000')
	}
	return {
		'^/(app|login|api|assets|files|private)': {
			target: `http://127.0.0.1:${webserver_port}`,
			ws: true,
		},
	}
}

function getCommonSiteConfig(): Record<string, any> | null {
	let currentDir = resolve('.')
	// traverse up till we find frappe-bench with sites directory
	while (currentDir !== '/') {
		if (existsSync(join(currentDir, 'sites'))) {
			const configPath = join(currentDir, 'sites', 'common_site_config.json')
			if (existsSync(configPath)) {
				const buffer = readFileSync(configPath)
				return JSON.parse(buffer.toString())
			}
			return null
		}
		currentDir = resolve(currentDir, '..')
	}
	return null
}
