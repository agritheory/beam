// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

import { ChildDoctype } from './index.js'

export type BaseContext = {
	action: string
	doctype: string
	parentfield?: string
	field: string
	target: string
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
	client?: Record<string, string[]>
	frm?: string[]
	listview?: string[]
	scannable_doctypes?: string[]
}
