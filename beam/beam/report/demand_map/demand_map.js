// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

frappe.query_reports['Demand Map'] = {
	filters: [
		{
			fieldname: 'order_by',
			fieldtype: 'Select',
			options: ['Oldest Unallocated', 'Oldest Allocated', 'Newest Allocated', 'Newest Unallocated'],
			default: 'Newest Unallocated',
			label: frappe._('Sort By'),
		},
		{
			fieldname: 'item_code',
			fieldtype: 'Link',
			label: frappe._('Item'),
			options: 'Item',
		},
	],
	formatter: function (value, row, column, data, default_formatter) {
		value = default_formatter(value, row, column, data)
		if (data && ['net_required_qty', 'total_required_qty'].includes(column.fieldname)) {
			if (data.net_required_qty <= data.allocated_qty) {
				value = `<span style="color: green">${value}</span>`
			} else if (!data.allocated_qty && data.net_required_qty) {
				value = `<span style="color: red">${value}</span>`
			} else if (data.allocated_qty > 0) {
				value = `<span style="color: orange">${value}</span>`
			} else if (data.indent == 1 && data.allocated_qty) {
				value = `<span style="color: green">${value}</span>`
			}
		}
		if (data && column.fieldname == 'allocated_qty') {
			if (data.net_required_qty <= data.allocated_qty) {
				value = `<span style="color: green">${value}</span>`
			} else if (!data.allocated_qty) {
				value = `<span style="color: red">${value}</span>`
			} else if (data.net_required_qty > data.allocated_qty) {
				value = `<span style="color: orange">${value}</span>`
			}
		}
		if (data && column.fieldname == 'status') {
			if (data.status == 'Unallocated') {
				value = `<span class="indicator-pill no-indicator-dot whitespace-nowrap red"><span>${value}</span></span>`
			} else if (data.status == 'Partially Allocated') {
				value = `<span class="indicator-pill no-indicator-dot whitespace-nowrap orange"><span>${value}</span></span>`
			} else if (data.status == 'Soft Allocated') {
				value = `<span class="indicator-pill no-indicator-dot whitespace-nowrap green"><span>${value}</span></span>`
			}
		}
		return value
	},
}
