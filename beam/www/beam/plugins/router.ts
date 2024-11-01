// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import { resolve } from 'path'

import type { HookConfig } from '@/types/config.js'
import { getAppConfigs, mergeConfigs, transformRoutes } from './hooks.js'

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
