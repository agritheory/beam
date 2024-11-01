// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import { readFileSync } from 'fs'
import { globSync } from 'glob'
import { resolve } from 'path'
import type { ComponentResolver } from 'unplugin-vue-components'

const HOOK_NAME = 'beam_mobile'

export function BEAMResolver(): ComponentResolver {
	const components = getComponentsFromHooks()
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

export function RouteResolver() {
	const appHooks = getHooks()
	const routes = {}
	for (const hookFile of appHooks) {
		const fileContent = readFileSync(hookFile, { encoding: 'utf-8' })
		if (fileContent.includes(HOOK_NAME)) {
			const extractedComponents = extractComponentsAndRoutes(fileContent)
			if (extractedComponents.routes) {
				console.log(`Custom BEAM routes found in ${hookFile}`)
				let _routes = transformRoutes(extractedComponents.routes)
				mergeConfigs(routes, _routes)
			}
		}
	}
	return Object.values(routes)
}

function getComponentsFromHooks() {
	const appHooks = getHooks()
	const components = {}
	for (const hookFile of appHooks) {
		const fileContent = readFileSync(hookFile, { encoding: 'utf-8' })
		if (fileContent.includes(HOOK_NAME)) {
			const extractedComponents = extractComponentsAndRoutes(fileContent)
			if (extractedComponents.components) {
				console.log(`Custom BEAM components found in ${hookFile}`)
				mergeConfigs(components, extractedComponents.components)
			}
		}
	}
	return components
}

function extractComponentsAndRoutes(fileContent: string): Object | undefined {
	let parsedConfig = {}
	const componentHookRegex = new RegExp(`${HOOK_NAME}\\s*=\\s*({[^]*?})(?=\\s*$|\\s*#|\\s*[\r\n])`)
	const match = fileContent.match(componentHookRegex)

	if (match) {
		try {
			parsedConfig = JSON.parse(preFormatHooks(match[1]))
		} catch (error) {
			console.error('Failed to parse hooks:', error)
			console.debug('Extracted content:', match[1])
			return undefined
		}
	}
	return parsedConfig
}

function preFormatHooks(rawText: string): string {
	let formattedText = rawText
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

	return formattedText
}

function mergeConfigs(...configs: Array<Record<string, string> | undefined>): Record<string, string> {
	return configs.reduce((result, config) => {
		Object.entries(config ?? {}).forEach(([key, value]) => (result[key] = value))
		return result
	}, {})
}

function transformRoutes(routes: any[]): Record<string, any> {
	return routes.reduce((acc, route) => {
		acc[route.path] = route
		return acc
	}, {})
}

function getHooks(): string[] {
	// respects installed app order
	const appsPath = resolve(process.cwd(), '..')
	const appsJSONpath = resolve(appsPath, '../sites/apps.json')
	const appsJSON = JSON.parse(readFileSync(appsJSONpath, { encoding: 'utf-8' }))
	const appHooks = globSync(`${appsPath}/**/hooks.py`)

	const appOrderMap = Object.entries(appsJSON).reduce(
		(acc, [appName, config]: [string, any]) => {
			acc[appName] = config.idx
			return acc
		},
		{} as Record<string, number>
	)

	return appHooks.sort((a, b) => {
		const appNameA = a.split('/').slice(-3)[0] // assumes ../app_name/*/hooks.py
		const appNameB = b.split('/').slice(-3)[0]

		const indexA = appOrderMap[appNameA] ?? Infinity
		const indexB = appOrderMap[appNameB] ?? Infinity

		return indexA - indexB
	})
}
