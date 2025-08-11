// Copyright (c) 2025, AgriTheory and contributors
// For license information, please see license.txt

frappe.ui.form.on('Purchase Receipt', {
	async refresh(frm) {
		await setup_scale(frm)
	},
})

async function setup_scale(frm) {
	$('.form-sidebar').append(`<div style="font-size: 300%; text-align: right">
	<p id="scale-readout"> 0.0 oz</p>
	<button id="use-scale" class="btn btn-lg btn-success">USE SCALE</button>
	</div>`)
	let scale_readout = $('#scale-readout')
	$('#use-scale').on('click', () => use_scale(scale_readout))
	let array_of_weight_readings = []
	let weighed = false
	let _mode = undefined
	async function use_scale(scale_readout) {
		$('#use-scale').hide()
		const device = (await navigator.hid.requestDevice({ filters: [] }))?.[0]
		await device.open()

		// think of this as a while loop
		device.oninputreport = report => {
			// check for "exit" or "weighed" flag
			const { value, unit } = parseScaleData(report.data)
			// detect if last __ on array are <= 0 as signal to move to next item
			//
			array_of_weight_readings.push(value)
			_mode = scale_readout.html(`${value} ${unit}`)
		}
	}
}

function parseScaleData(data) {
	const sign = Number(data.getUint8(0)) == 4 ? 1 : -1 // 4 = positive, 5 = negative, 2 = zero
	const unit = Number(data.getUint8(1)) == 2 ? 'g' : 'oz' // 2 = g, 11 = oz
	const value = Number(data.getUint16(3, true)) // this one needs little endian
	return { value: sign * (unit == 'oz' ? value / 10 : value), unit }
}

function mode(arr) {
	if (arr.filter((x, index) => arr.indexOf(x) == index).length == arr.length) return arr
	else
		return mode(
			arr
				.sort((x, index) => x - index)
				.map((x, index) => (arr.indexOf(x) != index ? x : null))
				.filter(x => x != null)
		)
}

function set_qty_uom_and_focus_on_next_qty_field(frm, qty, uom) {
	console.log(qty, uom)
}
