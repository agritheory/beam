import onScan from 'onscan.js'

const valid_doctypes = {
	listview: [
		'Item',
		'Warehouse',
		'Workstation',
		'Handling Unit',
		'Packing Slip',
		'Purchase Receipt',
		'Purchase Invoice',
		'Delivery Note',
		'Sales Invoice',
		'Stock Entry',
		'Stock Reconciliation',
	],
	frm: [
		'Purchase Receipt',
		'Purchase Invoice',
		'Delivery Note',
		'Packing Slip',
		'Sales Invoice',
		'Stock Entry',
		'Stock Reconciliation',
	],
}

function waitForElement(selector) {
	return new Promise(resolve => {
		if (document.querySelector(selector)) {
			return resolve(document.querySelector(selector))
		}
		const observer = new MutationObserver(mutations => {
			if (document.querySelector(selector)) {
				resolve(document.querySelector(selector))
				observer.disconnect()
			}
		})
		observer.observe(document.body, {
			childList: true,
			subtree: true,
		})
	})
}

waitForElement('[data-route]').then(element => {
	let observer = new MutationObserver(() => {
		new ScanHandler()
		// console.log(window.scanHandler.scanner.scannerDetectionData)
	})
	const config = { attributes: true, childList: false, characterData: true }
	observer.observe(element, config)
})

// document.dispatchEvent(new Event('scan', {data: {sCode: "3767127653309169910", iQty: 1}}))

class ScanHandler {
	constructor() {
		let me = this
		if (
			!window.hasOwnProperty('scanHandler') ||
			!window.scanHandler.hasOwnProperty('scanner') ||
			!window.scanHandler.scanner.isAttachedTo(document)
		) {
			me.scanner = onScan.attachTo(document, {
				onScan: async function (sCode, iQty) {
					await me.get_scanned_context(sCode, iQty)
				},
				ignoreIfFocusOn: '.frappe-input',
			})
			window.scanHandler = me
		}
	}
	reduceContext() {
		const route = frappe.get_route()
		if (route[0] == 'List' && valid_doctypes.listview.includes(route[1])) {
			return {
				listview: route[1],
			}
		} else if (route[0] == 'Form' && valid_doctypes.frm.includes(route[1])) {
			return {
				frm: route[1],
			}
		}
	}
	async get_scanned_context(sCode, iQty) {
		return new Promise(resolve => {
			const context = this.reduceContext()
			frappe.xcall('beam.beam.scan.scan', { barcode: sCode, context: context, current_qty: iQty }).then(r => {
				if (r && r.length) {
					resolve(this[String(r[0].action)](r))
				}
				// TODO: else error
			})
		})
	}
	route(barcode_context) {
		frappe.set_route('Form', barcode_context[0].field, barcode_context[0].target)
	}
	filter(barcode_context) {
		const filters_to_apply = barcode_context.map(filterset => {
			window.fltr.add_filter(filterset.doctype, filterset.field, '=', filterset.target)
		})
		Promise.all(filters_to_apply).then(() => {
			window.fltr.apply()
		})
	}
	add_or_associate(barcode_context) {
		if (barcode_context.length < 1) {
			return
		}
		barcode_context.forEach(field => {
			if (['Packing Slip'].includes(cur_frm.doc.doctype)) {
				if (
					!cur_frm.doc.items.some(row => {
						return (
							(row.item_code == field.context.item_code && !row.handling_unit) ||
							row.handling_unit == field.context.handling_unit
						)
					})
				) {
					if (!cur_frm.doc.items.length || !cur_frm.doc.items[0].item_code) {
						cur_frm.doc.items = []
					}
					let existing_row = cur_frm.doc.items.find(val => val.item_code == field.context.item_code)
					let row = cur_frm.add_child('items', field.context)
					row.source_warehouse = field.context.warehouse
					if (cur_frm.doc.operation && cur_frm.doc.operation.includes('Mixing - ')) row.required_qty = row.stock_qty = 0
					else row.required_qty = existing_row ? existing_row.required_qty : 0
					if (frappe.ui.form.handlers[row.doctype] && frappe.ui.form.handlers[row.doctype].uom) {
						frappe.ui.form.handlers[row.doctype].uom.map(r => {
							r(cur_frm, row.doctype, row.name)
						})
					}
					cur_frm.refresh_field('items')
				} else {
					let duplicate_row = null
					for (let row of cur_frm.doc.items) {
						if (
							(row.item_code == field.context.item_code && !row.handling_unit) ||
							row.handling_unit == field.context.handling_unit
						) {
							frappe.model.set_value(row.doctype, row.name, field.field, field.target)
							// if doctype is packing slip and user scanned handling unit
							// update handling unit's itemcode qty with handling unit qty and
							// create row with remaining qty annd without handling unit
							if (cur_frm.doc.doctype === 'Packing Slip' && field.field === 'handling_unit') {
								duplicate_row = { ...row }
								duplicate_row.qty -= field.context.qty
								if (duplicate_row.qty <= 0) {
									return
								}
								duplicate_row.handling_unit = null
								duplicate_row.name = null
								frappe.model.set_value(row.doctype, row.name, 'qty', field.context.qty)
							}
						}
					}
					if (duplicate_row) {
						cur_frm.add_child('items', duplicate_row)
						cur_frm.refresh_field('items')
					}
				}
			} else {
				if (
					!cur_frm.doc.items.some(row => {
						return (
							(row.item_code == field.context.item_code && row.stock_qty == field.context.stock_qty) ||
							row.handling_unit == field.context.handling_unit
						)
					})
				) {
					if (!cur_frm.doc.items.length || !cur_frm.doc.items[0].item_code) {
						cur_frm.doc.items = []
					}
					let row = cur_frm.add_child('items', field.context)
					if (frappe.ui.form.handlers[row.doctype] && frappe.ui.form.handlers[row.doctype].uom) {
						frappe.ui.form.handlers[row.doctype].uom.map(r => {
							r(cur_frm, row.doctype, row.name)
						})
					}
				} else {
					for (let row of cur_frm.doc.items) {
						if (
							(row.item_code == field.context.item_code && row.stock_qty == field.context.stock_qty) ||
							row.handling_unit == field.context.handling_unit
						) {
							// if ((row.item_code == handling_unit.item_code && row.stock_qty == handling_unit.stock_qty) || row.handling_unit == handling_unit.handling_unit) {
							frappe.model.set_value(row.doctype, row.name, field.field, field.target)
						}
					}
				}
			}
		})
		cur_frm.refresh_field('items')
	}
	set_warehouse(barcode_context) {
		if (barcode_context.length > 0) {
			barcode_context = barcode_context[0]
		} else {
			return
		}
		const source_warehouses = [
			'Send to Subcontractor',
			'Material Consumption for Manufacture',
			'Material Issue',
			'Material Transfer for Manufacture',
		]
		const target_warehouses = ['Material Transfer', 'Material Receipt', 'Manufacture']
		const both_warehouses = ['Repack']
		if (barcode_context.doctype == 'Stock Entry' && source_warehouses.includes(cur_frm.doc.stock_entry_type)) {
			cur_frm.set_value('from_warehouse', barcode_context.target)
			for (let row of cur_frm.doc.items) {
				frappe.model.set_value(row.doctype, row.name, 's_warehouse', barcode_context.target)
			}
		} else if (barcode_context.doctype == 'Stock Entry' && target_warehouses.includes(cur_frm.doc.stock_entry_type)) {
			cur_frm.set_value('to_warehouse', barcode_context.target)
			for (let row of cur_frm.doc.items) {
				frappe.model.set_value(row.doctype, row.name, 't_warehouse', barcode_context.target)
			}
		} else if (barcode_context.doctype == 'Stock Entry' && both_warehouses.includes(cur_frm.doc.stock_entry_type)) {
			cur_frm.set_value('from_warehouse', barcode_context.target)
			cur_frm.set_value('to_warehouse', barcode_context.target)
			for (let row of cur_frm.doc.items) {
				frappe.model.set_value(row.doctype, row.name, 's_warehouse', barcode_context.target)
				frappe.model.set_value(row.doctype, row.name, 't_warehouse', barcode_context.target)
			}
		}
	}
	add_or_increment(barcode_context) {
		if (barcode_context.length > 0) {
			barcode_context = barcode_context[0]
		} else {
			return
		}
		// if not item code, add row
		// else find last row with item code and increment
		if (
			!cur_frm.doc.items.some(row => {
				return (
					(row.item_code == barcode_context.context.item_code && !row.handling_unit) ||
					row.barcode == barcode_context.context.barcode
				)
			})
		) {
			if (!cur_frm.doc.items.length || !cur_frm.doc.items[0].item_code) {
				cur_frm.doc.items = []
			}
			cur_frm.add_child('items', barcode_context.context)
		} else {
			for (let row of cur_frm.doc.items) {
				if (
					(row.item_code == barcode_context.context.item_code && !row.handling_unit) ||
					row.barcode == barcode_context.context.barcode
				) {
					frappe.model.set_value(row.doctype, row.name, 'qty', row.qty + 1)
				}
			}
		}
		cur_frm.refresh_field('items')
	}
}
