// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

frappe.query_reports['Demand Map'] = {
	filters: [],
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data)
		if (data && column.fieldname == 'actual_qty') {
			if (data.net_required_qty == data.actual_qty) {
				value = `<span style="color: green">${value}</span>`
			}
		}
		return value
	},
}
