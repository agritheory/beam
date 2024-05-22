frappe.provide('beam')

// eslint-disable-next-line no-undef
beam.show_message = function () {
	frappe.msgprint('example callback')
}
