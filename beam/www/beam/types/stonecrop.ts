// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import { CSSProperties } from 'vue'

/**
 * Configuration object for ListView component items
 * @public
 */
export type ListViewItem = {
	barcode?: string
	checked?: boolean
	count?: {
		count: number
		of: number
		uom?: string
		editable?: boolean
	}
	date?: string
	dateFormat?: string
	debounce?: number
	description?: string
	label?: string
	linkComponent?: string
	route?: string
}

/**
 * Union type for color values - supports RGB, RGBA, HEX, HSL, HSLA, or CSS color string
 * @public
 */
export type BeamColor = RGB | RGBA | HEX | HSL | HSLA | CSSProperties['color']

/**
 * Filter choice with label and value for BeamFilter component
 * @public
 */
export type BeamFilterChoice = {
	label: string
	value: string
}

/**
 * RGB color string representation
 * @public
 */
export type RGB = `rgb(${number}, ${number}, ${number})`

/**
 * RGBA color string representation
 * @public
 */
export type RGBA = `rgba(${number}, ${number}, ${number}, ${number})`

/**
 * HSL color string representation
 * @public
 */
export type HSL = `hsl(${number}, ${number}%, ${number}%)`

/**
 * HSLA color string representation
 * @public
 */
export type HSLA = `hsl(${number}, ${number}%, ${number}%), ${number}`

/**
 * HEX color string representation
 * @public
 */
export type HEX = `#${string}`
