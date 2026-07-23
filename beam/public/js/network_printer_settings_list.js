// Copyright (c) 2025, AgriTheory and contributors
// For license information, please see license.txt

frappe.provide('beam')

const HIDDEN_NPS_VIEWS = new Set(['Dashboard', 'Report', 'Gantt', 'Kanban', 'Calendar', 'Image', 'Tree', 'Map'])

const NPS_DOCTYPE = 'Network Printer Settings'

function redirect_nps_dashboard_to_printer_queue() {
	const route = frappe.get_route()
	if (route[0] === 'List' && route[1] === NPS_DOCTYPE && (route[2] || '').toLowerCase() === 'dashboard') {
		frappe.set_route('printer-queue')
	}
}

if (!frappe.views.ListViewSelect.prototype.add_view_to_menu_patched_for_nps) {
	const original_add_view_to_menu = frappe.views.ListViewSelect.prototype.add_view_to_menu
	frappe.views.ListViewSelect.prototype.add_view_to_menu = function add_view_to_menu(view, action) {
		if (this.doctype === NPS_DOCTYPE && HIDDEN_NPS_VIEWS.has(view)) {
			return
		}
		return original_add_view_to_menu.call(this, view, action)
	}
	frappe.views.ListViewSelect.prototype.add_view_to_menu_patched_for_nps = true
}

if (!frappe.views.BaseList.prototype.setup_view_menu_patched_for_nps) {
	const original_setup_view_menu = frappe.views.BaseList.prototype.setup_view_menu
	frappe.views.BaseList.prototype.setup_view_menu = function setup_view_menu() {
		original_setup_view_menu.apply(this, arguments)
		if (this.doctype !== NPS_DOCTYPE || !this.views_menu) {
			return
		}
		this.page.add_custom_menu_item(
			this.views_menu,
			__('Printer Queue'),
			() => frappe.set_route('printer-queue'),
			true,
			null,
			'printer'
		)
	}
	frappe.views.BaseList.prototype.setup_view_menu_patched_for_nps = true
}

if (!beam.network_printer_settings_route_bound) {
	beam.network_printer_settings_route_bound = true
	frappe.router.on('change', redirect_nps_dashboard_to_printer_queue)
}
