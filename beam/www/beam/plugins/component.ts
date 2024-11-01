import type { ComponentResolver, Options } from 'unplugin-vue-components'

import { HookConfig } from '@/types/config.js'
import { getAppConfigs, mergeConfigs } from './hooks.js'

export function getComponentPluginOptions(): Options {
	// let globs: Options['globs']
	// const components = getComponents()
	// if ('*' in components) {
	// 	globs = components['*']
	// 	delete components['*']
	// }

	const dts: Options['dts'] = 'beam/www/beam/components.d.ts'
	const resolvers: Options['resolvers'] = [BEAMResolver()]

	return {
		dts,
		resolvers,
	}
}

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
