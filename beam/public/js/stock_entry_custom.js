frappe.ui.form.on('Stock Entry', {
	async before_cancel(frm) {
		await set_recombine_handling_units(frm)
	},
	setup: function (frm) {
		frm.set_query('handling_unit', 'items', function (doc, cdt, cdn) {
			let row = locals[cdt][cdn]
			if (!row.item_code) {
				return
			}
			return {
				query: 'beam.beam.overrides.stock_entry.get_handling_units_for_item_code',
				filters: {
					item_code: row.item_code,
				},
			}
		})
	},
})

async function show_handling_unit_recombine_dialog(frm) {
	const data = await get_handling_units(frm)
	if (!data) {
		return resolve({})
	}
	let fields = [
		{
			fieldtype: 'Data',
			fieldname: 'row_name',
			in_list_view: 0,
			read_only: 1,
			disabled: 0,
			hidden: 1,
		},
		{
			fieldtype: 'Link',
			fieldname: 'item_code',
			options: 'Item',
			in_list_view: 1,
			read_only: 1,
			disabled: 0,
			label: __('Item Code'),
		},
		{
			fieldtype: 'Data',
			fieldname: 'item_name',
			in_list_view: 0,
			disabled: 0,
			hidden: 1,
		},
		{
			fieldtype: 'Data',
			fieldname: 'handling_unit',
			label: __('Handling Unit'),
			in_list_view: 1,
			read_only: 1,
		},
		{
			fieldtype: 'Float',
			fieldname: 'remaining_qty',
			label: __('Remaining Qty'),
			in_list_view: 1,
			read_only: 1,
		},
		{
			fieldtype: 'Data',
			fieldname: 'to_handling_unit',
			label: __('Handling Unit to recombine'),
			in_list_view: 1,
			read_only: 1,
		},
		{
			fieldtype: 'Float',
			fieldname: 'transferred_qty',
			label: __('Transferred Qty'),
			in_list_view: 1,
			read_only: 1,
		},
	]

	return new Promise(resolve => {
		let dialog = new frappe.ui.Dialog({
			title: __('Please select Handling Units to re-combine'),
			fields: [
				{
					fieldname: 'handling_units',
					fieldtype: 'Table',
					in_place_edit: false,
					editable_grid: false,
					cannot_add_rows: true,
					cannot_delete_rows: true,
					reqd: 1,
					data: data,
					get_data: () => {
						return data
					},
					fields: fields,
					description: __(
						'Please select Handling Units to re-combine. Unselected Handling Units will be returned to inventory with their new quantities and Handling Units'
					),
				},
			],
			primary_action: () => {
				let to_recombine = dialog.fields_dict.handling_units.grid.get_selected_children().map(row => {
					return row.row_name
				})
				dialog.hide()
				return resolve(to_recombine)
			},
			primary_action_label: __('Cancel and Recombine'),
			size: 'extra-large',
		})
		dialog.show()
		dialog.get_close_btn()
	})
}

async function get_handling_units(frm) {
	let handling_units = []
	for (const row of frm.doc.items) {
		if (row.handling_unit && row.to_handling_unit) {
			let remaining_qty = await get_handling_unit_stock_qty(frm.doc.name, row.handling_unit, row.s_warehouse)
			handling_units.push({
				row_name: row.name,
				item_code: row.item_code,
				item_name: row.item_name,
				handling_unit: row.handling_unit,
				to_handling_unit: row.to_handling_unit,
				remaining_qty: remaining_qty,
				transferred_qty: row.qty,
			})
		}
	}
	return handling_units
}
async function get_handling_unit_stock_qty(name, handling_unit, s_warehouse) {
	let result = await frappe.xcall('beam.beam.overrides.stock_entry.get_handling_unit_qty', {
		voucher_no: name,
		handling_unit: handling_unit,
		warehouse: s_warehouse,
	})
	return flt(result)
}

//re combine
async function set_recombine_handling_units(frm) {
	let to_recombine = await show_handling_unit_recombine_dialog(frm)
	await frappe.xcall('beam.beam.overrides.stock_entry.set_rows_to_recombine', {
		docname: frm.doc.name,
		to_recombine: to_recombine,
	})
}
