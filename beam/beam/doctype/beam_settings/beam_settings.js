// Copyright (c) 2024, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on('BEAM Settings', {
	onload_post_render: frm => {
		frm.fields_dict.routes.grid.update_docfield_property('component', 'options', frm.doc.__onload.components)
	},
})

frappe.ui.form.on('BEAM Mobile Route', {
	routes_add: frm => {
		frm.fields_dict.routes.grid.update_docfield_property('component', 'options', frm.doc.__onload.components)
	},
})
