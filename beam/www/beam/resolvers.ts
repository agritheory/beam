// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import { readFileSync } from 'fs'
import { globSync } from 'glob'
import { resolve } from 'path'
import type { ComponentResolver } from 'unplugin-vue-components'

import type { AppList, HookConfig, HookRoute } from './types/config.js'

const HOOK_NAME = 'beam_mobile'

export function BEAMResolver(): ComponentResolver {
	const components = getComponents()
	return {
		type: 'component',
		resolve: name => {
			if (components[name]) {
				return {
					name,
					from: components[name],
				}
			}
		},
	}
}

export function getRoutes(): HookConfig['routes'] {
	const appConfigs = getAppConfigs()
	let routes = {}
	for (const config of appConfigs) {
		if (config.routes) {
			console.log(`Custom BEAM routes found in ${config.file}`)
			const _routes = transformRoutes(config.routes)
			routes = mergeConfigs(routes, _routes)
		}
	}
	return Object.values(routes)
}

export function getComponents(): HookConfig['components'] {
	const appConfigs = getAppConfigs()
	let components = {}
	for (const config of appConfigs) {
		if (config.components) {
			console.log(`Custom BEAM components found in ${config.file}`)
			components = mergeConfigs(components, config.components)
		}
	}
	return components
}

export function getComponentPaths(): Record<string, string> {
	const appsPath = resolve(process.cwd(), '..')
	const appConfigs = getAppConfigs()
	let paths = {}
	for (const config of appConfigs) {
		if (config.components) {
			const componentPaths = Object.entries(config.components).reduce(
				(acc, [name, path]) => {
					acc[name] = resolve(appsPath, path)
					return acc
				},
				{} as Record<string, string>
			)
			paths = mergeConfigs(paths, componentPaths)
		}
	}
	return paths
}

function getAppConfigs(): HookConfig[] {
	const appHooks = getAppHooks()
	const configs = []
	for (const hookFile of appHooks) {
		const fileContent = readFileSync(hookFile, { encoding: 'utf-8' })
		if (fileContent.includes(HOOK_NAME)) {
			const config = extractConfig(fileContent)
			if (config) {
				config.file = hookFile
				configs.push(config)
			}
		}
	}
	return configs
}

function getAppHooks(): string[] {
	// respects installed app order
	const appsPath = resolve(process.cwd(), '..')
	const appsListPath = resolve(appsPath, '../sites/apps.json')
	const appsList: AppList = JSON.parse(readFileSync(appsListPath, { encoding: 'utf-8' }))
	const appHooks = globSync(`${appsPath}/**/hooks.py`)

	const appOrderMap = Object.entries(appsList).reduce(
		(acc, [appName, config]) => {
			acc[appName] = config.idx
			return acc
		},
		{} as Record<string, number>
	)

	return appHooks.sort((prevHook, nextHook) => {
		const appNameA = prevHook.split('/').slice(-3)[0] // assumes ../app_name/*/hooks.py
		const appNameB = nextHook.split('/').slice(-3)[0]

		const indexA = appOrderMap[appNameA] ?? Infinity
		const indexB = appOrderMap[appNameB] ?? Infinity

		return indexA - indexB
	})
}

function extractConfig(fileContent: string): HookConfig | undefined {
	const hookRegex = new RegExp(`${HOOK_NAME}\\s*=\\s*({[^]*?})(?=\\s*$|\\s*#|\\s*[\r\n])`)
	const match = fileContent.match(hookRegex)

	if (match) {
		try {
			const formattedConfig = preFormatHooks(match[1])
			return JSON.parse(formattedConfig)
		} catch (error) {
			console.error('Failed to parse hooks:', error)
			console.debug('Extracted content:', match[1])
			return
		}
	}
}

function preFormatHooks(rawText: string): string {
	return (
		rawText
			// Remove comments first
			.replace(/^\s*#.*$/gm, '') // Remove full-line comments
			.replace(/(.+?)#.*$/gm, '$1') // Remove inline comments
			// Convert Python syntax to JavaScript
			.replace(/'/g, '"') // Replace single quotes
			.replace(/True/g, 'true') // Convert booleans
			.replace(/False/g, 'false')
			.replace(/None/g, 'null') // Convert None to null
			// Clean up JSON structure
			.replace(/,(\s*[\]}])/g, '$1') // Remove trailing commas
			.replace(/\s+/g, ' ') // Normalize whitespace
			.replace(/\t/g, ' ') // Replace tabs with spaces
			.trim()
	)
}

function mergeConfigs(...configs: Array<Record<string, any> | undefined>): Record<string, any> {
	return configs.reduce((result, config) => {
		Object.entries(config ?? {}).forEach(([key, value]) => (result[key] = value))
		return result
	}, {})
}

function transformRoutes(routes: HookConfig['routes']): Record<string, HookRoute> {
	return routes.reduce((acc, route) => {
		acc[route.path] = route
		return acc
	}, {})
}
