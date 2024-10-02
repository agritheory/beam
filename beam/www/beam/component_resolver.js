// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import * as path from 'path'
import * as fs from 'fs'
import { globSync } from 'glob'

// import type { ComponentResolver } from '../../types'
// typing https://github.com/unplugin/unplugin-vue-components/blob/main/src/types.ts#L34C1-L41C84

export function BEAMResolver() {
	return {
		type: 'component',
		resolve: name => {
			let components = getComponentsFromHooks()
			console.log(components)
			if (name.match(/^I[A-Z]/)) {
				return {
					name,
					from: '@inkline/inkline',
				}
			}
		},
	}
}

function getComponentsFromHooks() {
	let appsPath = path.resolve(process.cwd(), '..')
	let hooks = globSync(`${appsPath}/**/hooks.py`)
	let components = []
	hooks.forEach(h => {
		fs.readFile(h, { encoding: 'utf-8' }, (err, data) => {
			if (data.includes('beam_components')) {
				components.append(extractBEAMComponents(data))
			} else {
				console.log(`No BEAM components found in ${h}`)
			}
		})
	})
	return components
}

function extractBEAMComponents(pythonCode) {
	const beamComponentsRegex = /beam_components\s*=\s*{([^}]+)}/

	const match = pythonCode.match(beamComponentsRegex)

	if (match) {
		const dictContents = match[1].trim()
		const pairs = dictContents.split(',').map(pair => pair.trim())
		const result = {}
		pairs.forEach(pair => {
			const [key, value] = pair.split(':').map(item => item.trim())
			result[key.replace(/['"]/g, '')] = value.replace(/['"]/g, '')
		})

		return result
	}

	return null
}
