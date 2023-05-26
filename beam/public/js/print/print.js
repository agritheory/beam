frappe.ui.form.on('Stock Entry', {
	refresh(frm) {
		custom_print_button(frm)
	},
})
frappe.ui.form.on('Stock Reconciliation', {
	refresh(frm) {
		custom_print_button(frm)
	},
})
frappe.ui.form.on('Purchase Invoice', {
	refresh(frm) {
		if (frm.doc.update_stock) {
			custom_print_button(frm)
		}
	},
})
frappe.ui.form.on('Purchase Receipt', {
	refresh(frm) {
		custom_print_button(frm)
	},
})
frappe.ui.form.on('Sales Invoice', {
	refresh(frm) {
		if (frm.doc.update_stock) {
			custom_print_button(frm)
		}
	},
})
frappe.ui.form.on('Delivery Note', {
	refresh(frm) {
		custom_print_button(frm)
	},
})

function custom_print_button(frm) {
	if (frm.doc.docstatus != 1) {
		return
	}
	frm.add_custom_button(__('<span class="fa fa-print"></span> Print Handling Unit'), () => {
		let d = new frappe.ui.Dialog({
			title: __('Select Printer Setting'),
			fields: [
				{
					label: __('Printer Setting'),
					fieldname: 'printer_setting',
					fieldtype: 'Link',
					options: 'Network Printer Settings',
					default: 'Shipping',
				},
				{
					label: __('Printer Format'),
					fieldname: 'print_format',
					fieldtype: 'Link',
					options: 'Print Format',
					get_query: function () {
						return {
							filters: { doc_type: 'Handling Unit' },
						}
					},
				},
			],
			primary_action_label: 'Select',
			primary_action(selection) {
				d.hide()
				frappe.call({
					method: 'beam.beam.printing.print_handling_units',
					args: {
						doctype: frm.doc.doctype,
						name: frm.doc.name,
						printer_setting: selection.printer_setting,
						print_format: selection.print_format,
						doc: frm.doc,
					},
				})
			},
		})
		d.show()
	})
}
