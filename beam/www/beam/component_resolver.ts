// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import { readFileSync } from 'fs'
import { globSync } from 'glob'
import { resolve } from 'path'
import type { ComponentResolver } from 'unplugin-vue-components'

const HOOK_NAME = 'beam_components'

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

function getComponentsFromHooks() {
	const appsPath = resolve(process.cwd(), '..')
	const appHooks = globSync(`${appsPath}/**/hooks.py`)

	const components = {}
	for (const hookFile of appHooks) {
		const fileContent = readFileSync(hookFile, { encoding: 'utf-8' })
		if (fileContent.includes(HOOK_NAME)) {
			const extractedComponents = extractComponents(fileContent)
			if (extractedComponents) {
				console.log(`Custom BEAM components found in ${hookFile}`)
				Object.assign(components, extractedComponents)
			}
		}
	}

	return components
}

function extractComponents(fileContent: string): Record<string, string> | undefined {
	const componentHookRegex = new RegExp(`${HOOK_NAME}\\s*=\\s*{([^}]+)}`)
	const match = fileContent.match(componentHookRegex)
	if (match) {
		const dictContents = match[1].trim()
		const pairs = dictContents
			.split(',')
			.map(pair => pair.trim())
			.filter(Boolean)
		const result = {}
		pairs.forEach(pair => {
			const [key, value] = pair.split(':').map(item => item.trim())
			result[key.replace(/['"]/g, '')] = value.replace(/['"]/g, '')
		})
		return result
	}
}
