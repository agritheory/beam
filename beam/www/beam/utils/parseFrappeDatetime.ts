// Copyright (c) 2026, AgriTheory and contributors
// For license information, please see license.txt

/** Frappe datetimes use a space separator and up to six fractional digits; Safari needs ISO 8601. */
export function parseFrappeDatetime(value: string): number {
	if (!value) return NaN
	let normalized = value.replace(' ', 'T')
	const dot = normalized.indexOf('.')
	if (dot !== -1) {
		normalized = normalized.slice(0, dot + 4)
	}
	return new Date(normalized).getTime()
}
