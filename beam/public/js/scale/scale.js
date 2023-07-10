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

	async function use_scale(scale_readout) {
		$('#use-scale').html('WEIGH')
		$('#use-scale').on('click', () => {
			console.log()
		})
		// when item is weighed, set value for qty and uom in last row

		const device = (await navigator.hid.requestDevice({ filters: [] }))?.[0]
		await device.open()
		// think of this as a while loop
		device.oninputreport = report => {
			// check for "exit" or "weighed" flag
			const { value, unit } = parseScaleData(report.data)
			scale_readout.html(`${value} ${unit}`)
		}
	}

	function parseScaleData(data) {
		const sign = Number(data.getUint8(0)) == 4 ? 1 : -1 // 4 = positive, 5 = negative, 2 = zero
		const unit = Number(data.getUint8(1)) == 2 ? 'g' : 'oz' // 2 = g, 11 = oz
		const value = Number(data.getUint16(3, true)) // this one needs little endian
		return { value: sign * (unit == 'oz' ? value / 10 : value), unit }
	}
}
