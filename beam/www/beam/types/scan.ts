// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import type { ChildDoctype } from '@/types/index.js'

export type BaseContext = {
	/**
	 * The action to be performed on the scanned item.
	 * @example
	 * 'add_or_associate'
	 * 'add_or_increment'
	 * 'filter'
	 * 'route'
	 * 'set_item_code_and_handling_unit'
	 * 'set_warehouse'
	 */
	action: string

	doctype: string

	/**
	 * The field to be set on the target document.
	 * @example
	 * 'item_code'
	 * 'warehouse'
	 * 'handling_unit'
	 * 'qty'
	 */
	field: string

	/**
	 * The value to be set on the field.
	 */
	target: any
}

export type FormContext = BaseContext & {
	context: ChildDoctype
}

export type ListContext = BaseContext & {
	context: string
}

export type ScanContext = {
	frm?: string
	listview?: string
}

export type ScanConfig = {
	client?: Record<string, string[]>[]
	frm?: string[]
	listview?: string[]
	scannable_doctypes?: string[]
}
