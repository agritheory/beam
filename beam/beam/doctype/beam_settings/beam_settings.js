// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

frappe.dom.set_style(`
	.barcode-auto-generate-editor input[type="checkbox"]:not(:checked) + .label-area {
		text-decoration: line-through;
		color: var(--text-muted);
	}
`)

frappe.ui.form.on('BEAM Settings', {
	refresh(frm) {
		const wrapper = $(frm.fields_dict.barcode_exclusions_html.wrapper)
		wrapper.empty()
		wrapper.addClass('barcode-auto-generate-editor').css({
			border: '1px solid var(--border-color)',
			borderRadius: 'var(--border-radius)',
			padding: 'var(--padding-md)',
		})
		frm.barcode_exclusions_editor = new BEAMBarcodeAutoGenerateEditor(wrapper, frm)
	},
})

class BEAMBarcodeAutoGenerateEditor {
	constructor(wrapper, frm) {
		this.wrapper = wrapper
		this.frm = frm
		this.setup()
	}

	get allowed() {
		try {
			return JSON.parse(this.frm.doc.auto_barcode_doctypes || '["Item", "Warehouse"]')
		} catch {
			return ['Item', 'Warehouse']
		}
	}

	setup() {
		this.multicheck = frappe.ui.form.make_control({
			parent: this.wrapper,
			df: {
				fieldname: 'auto_barcode_doctypes',
				fieldtype: 'MultiCheck',
				select_all: true,
				columns: '15rem',
				get_data: () => {
					return frappe
						.xcall('beam.beam.doctype.beam_settings.beam_settings.get_doctypes_with_item_barcodes')
						.then(doctypes => {
							const allowed = this.allowed
							return doctypes.map(dt => ({
								label: __(dt),
								value: dt,
								checked: allowed.includes(dt),
							}))
						})
				},
				on_change: () => {
					this.sync_json()
					this.frm.dirty()
				},
			},
			render_input: true,
		})
	}

	sync_json() {
		const checked = this.multicheck.get_checked_options()
		frappe.model.set_value(this.frm.doctype, this.frm.docname, 'auto_barcode_doctypes', JSON.stringify(checked))
	}
}
