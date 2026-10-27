// Copyright (c) 2026, AgriTheory and contributors
// For license information, please see license.txt

declare const frappe: any

export function defaultCompany(): string | undefined {
	if (typeof frappe === 'undefined') return undefined
	return frappe.defaults?.get_user_default?.('Company') || frappe.boot?.sysdefaults?.company
}
