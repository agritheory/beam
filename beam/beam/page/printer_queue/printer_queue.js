// Copyright (c) 2025, AgriTheory and contributors
// For license information, please see license.txt

frappe.pages['printer-queue'].on_page_load = function (wrapper) {
	wrapper.printer_queue = new beam.PrinterQueueController(wrapper)
}

frappe.pages['printer-queue'].refresh = function (wrapper) {
	wrapper.printer_queue?.on_page_show()
}

frappe.provide('beam')

beam.PRINTER_QUEUE_POLL_INTERVAL_MS = 4000

beam.PrinterQueueController = class PrinterQueueController {
	constructor(wrapper) {
		this.wrapper = wrapper
		this.page = frappe.ui.make_app_page({
			parent: wrapper,
			title: __('Printer Queue'),
			single_column: true,
		})
		this.task_id = null
		this.jobs = []
		this.errors = []
		this.completed_since = null
		this.poll_timer = null
		this.starting_session = false
		this.polling = false
		this.can_cancel = frappe.model.can_write('Network Printer Settings')
		this.make_toolbar()
		this.make_table()
		this.bind_route_guard()
		this.on_page_show()
	}

	make_toolbar() {
		this.page.add_inner_button(__('Network Printer Settings'), () => {
			frappe.set_route('List', 'Network Printer Settings')
		})

		this.search_field = this.page.add_field({
			fieldname: 'search',
			label: __('Search'),
			fieldtype: 'Data',
			change: () => this.render_table(),
		})
	}

	make_table() {
		this.$main = $(`<div class="printer-queue-page"></div>`).appendTo(this.page.main)
		this.$errors = $(`<div class="printer-queue-errors mb-3"></div>`).appendTo(this.$main)
		this.$table_wrap = $(`<div class="table-responsive"></div>`).appendTo(this.$main)
		this.$table = $(`
			<table class="table table-bordered printer-queue-table">
				<thead></thead>
				<tbody></tbody>
			</table>
		`).appendTo(this.$table_wrap)
	}

	bind_route_guard() {
		if (beam.printer_queue_route_bound) {
			return
		}
		beam.printer_queue_route_bound = true
		frappe.router.on('change', () => {
			if (!beam.is_printer_queue_route()) {
				beam.PrinterQueueController.stop_active_session()
			}
		})
	}

	static active_controller = null

	static stop_active_session() {
		beam.PrinterQueueController.active_controller?.stop_session()
	}

	on_page_show() {
		if (!beam.is_printer_queue_route()) {
			return
		}
		beam.PrinterQueueController.active_controller = this
		this.start_session()
	}

	start_session() {
		if (this.task_id || this.starting_session) {
			return
		}
		this.starting_session = true
		frappe.call({
			method: 'beam.beam.printer_queue.start_printer_queue_watcher',
			freeze: true,
			freeze_message: __('Connecting to print server...'),
			callback: ({ message }) => {
				this.starting_session = false
				if (!message?.task_id) {
					return
				}
				this.task_id = message.task_id
				this.apply_snapshot(message)
				this.start_polling()
			},
			error: () => {
				this.starting_session = false
			},
		})
	}

	stop_session() {
		if (this.poll_timer) {
			clearInterval(this.poll_timer)
			this.poll_timer = null
		}
		if (this.task_id) {
			const task_id = this.task_id
			this.task_id = null
			this.completed_since = null
			frappe.call({
				method: 'beam.beam.printer_queue.stop_printer_queue_watcher',
				args: { task_id },
			})
		}
		if (beam.PrinterQueueController.active_controller === this) {
			beam.PrinterQueueController.active_controller = null
		}
	}

	start_polling() {
		if (this.poll_timer) {
			clearInterval(this.poll_timer)
		}
		this.poll_timer = setInterval(() => {
			this.poll_queue()
		}, beam.PRINTER_QUEUE_POLL_INTERVAL_MS)
	}

	poll_queue() {
		if (!this.task_id || this.polling) {
			return
		}
		this.polling = true
		frappe.call({
			method: 'beam.beam.printer_queue.poll_printer_queue',
			args: { task_id: this.task_id },
			callback: ({ message }) => {
				this.polling = false
				if (!message) {
					return
				}
				if (message.expired) {
					this.stop_session()
					this.start_session()
					return
				}
				this.apply_snapshot(message)
			},
			error: () => {
				this.polling = false
			},
		})
	}

	apply_snapshot(data) {
		if (data.completed_since != null) {
			this.completed_since = data.completed_since
		}
		const incoming = data.jobs || []
		const merged = new Map()

		for (const job of incoming) {
			merged.set(this.job_row_key(job), job)
		}

		for (const job of this.jobs) {
			const key = this.job_row_key(job)
			if (merged.has(key)) {
				continue
			}
			if (this.is_terminal_job(job) && this.job_in_session_window(job)) {
				merged.set(key, job)
			}
		}

		this.jobs = this.sort_jobs(Array.from(merged.values()))
		this.errors = data.errors || []
		this.render_errors()
		this.render_table()
	}

	job_in_session_window(job) {
		if (this.completed_since == null) {
			return false
		}
		const finished = job.time_at_completed || job.time_at_creation || 0
		return finished >= this.completed_since
	}

	job_row_key(job) {
		return `${job.server_ip}:${job.port}:${job.job_id}`
	}

	is_terminal_job(job) {
		const status = job.display_status || job.job_state
		return ['printed', 'completed', 'cancelled', 'aborted'].includes(status)
	}

	sort_jobs(jobs) {
		const active_states = new Set(['pending', 'held', 'processing', 'stopped'])
		return jobs.sort((left, right) => {
			const left_active = active_states.has(left.job_state)
			const right_active = active_states.has(right.job_state)
			if (left_active !== right_active) {
				return left_active ? -1 : 1
			}
			const left_finished = left.time_at_completed || left.time_at_creation || 0
			const right_finished = right.time_at_completed || right.time_at_creation || 0
			if (left_finished !== right_finished) {
				return right_finished - left_finished
			}
			return right.job_id - left.job_id
		})
	}

	render_errors() {
		this.$errors.empty()
		if (!this.errors.length) {
			return
		}
		for (const error of this.errors) {
			this.$errors.append(
				`<div class="alert alert-warning">${frappe.utils.escape_html(error.server_label)}: ${frappe.utils.escape_html(
					error.message
				)}</div>`
			)
		}
	}

	get_filtered_jobs() {
		const query = (this.search_field?.get_value() || '').trim().toLowerCase()
		if (!query) {
			return this.jobs
		}
		return this.jobs.filter(job => {
			const haystack = [
				job.job_id,
				job.job_name,
				job.user,
				job.printer,
				job.server_label,
				job.job_state,
				job.display_status,
			]
				.join(' ')
				.toLowerCase()
			return haystack.includes(query)
		})
	}

	render_table() {
		const jobs = this.get_filtered_jobs()
		const columns = [
			{ id: 'job_id', label: __('Job ID') },
			{ id: 'job_name', label: __('Document') },
			{ id: 'user', label: __('User') },
			{ id: 'job_state', label: __('Status') },
			{ id: 'printer', label: __('Printer') },
			{ id: 'server_label', label: __('Server') },
			{ id: 'submitted', label: __('Submitted') },
			{ id: 'finished', label: __('Finished') },
			{ id: 'pages', label: __('Pages') },
		]
		if (this.can_cancel) {
			columns.push({ id: 'actions', label: '' })
		}

		const $thead = this.$table.find('thead').empty()
		const $head_row = $('<tr></tr>').appendTo($thead)
		for (const column of columns) {
			$head_row.append(`<th>${column.label}</th>`)
		}

		const $tbody = this.$table.find('tbody').empty()
		if (!jobs.length) {
			const colspan = columns.length
			$tbody.append(`<tr><td colspan="${colspan}" class="text-muted text-center">${__('No print jobs.')}</td></tr>`)
			return
		}

		for (const job of jobs) {
			const $row = $('<tr></tr>').appendTo($tbody)
			$row.append(`<td>${frappe.utils.escape_html(String(job.job_id))}</td>`)
			$row.append(`<td>${frappe.utils.escape_html(job.job_name || '')}</td>`)
			$row.append(`<td>${frappe.utils.escape_html(job.user || '')}</td>`)
			$row.append(`<td>${this.render_status_badge(job)}</td>`)
			$row.append(`<td>${frappe.utils.escape_html(job.printer || '')}</td>`)
			$row.append(`<td>${frappe.utils.escape_html(job.server_label || '')}</td>`)
			$row.append(`<td>${this.format_timestamp(job.time_at_creation)}</td>`)
			$row.append(`<td>${this.format_timestamp(job.time_at_completed)}</td>`)
			$row.append(`<td>${frappe.utils.escape_html(this.format_pages(job))}</td>`)
			if (this.can_cancel) {
				const $actions = $('<td></td>').appendTo($row)
				if (this.can_cancel_job(job)) {
					$actions.append(
						`<button class="btn btn-xs btn-default" data-job-id="${
							job.job_id
						}" data-server-ip="${frappe.utils.escape_html(job.server_ip)}" data-port="${job.port}">${__(
							'Cancel'
						)}</button>`
					)
				}
			}
		}

		this.$table.find('button[data-job-id]').on('click', event => {
			const $btn = $(event.currentTarget)
			this.cancel_job($btn.data('job-id'), $btn.data('server-ip'), $btn.data('port'))
		})
	}

	can_cancel_job(job) {
		return ['pending', 'held', 'processing', 'stopped'].includes(job.job_state)
	}

	render_status_badge(job) {
		const state = job.display_status || job.job_state || 'unknown'
		const color_map = {
			pending: 'orange',
			held: 'yellow',
			processing: 'blue',
			stopped: 'red',
			cancelled: 'gray',
			aborted: 'red',
			completed: 'green',
			printed: 'green',
		}
		const color = color_map[state] || 'gray'
		const label = __(state)
		return `<span class="indicator ${color}">${frappe.utils.escape_html(label)}</span>`
	}

	format_timestamp(unix_time) {
		if (!unix_time) {
			return ''
		}
		return frappe.datetime.str_to_user(
			frappe.datetime.convert_to_user_tz(moment.unix(unix_time).format('YYYY-MM-DD HH:mm:ss'))
		)
	}

	format_pages(job) {
		if (job.pages == null) {
			return ''
		}
		if (job.pages_completed != null) {
			return `${job.pages_completed}/${job.pages}`
		}
		return String(job.pages)
	}

	cancel_job(job_id, server_ip, port) {
		frappe.confirm(__('Cancel print job {0}?', [job_id]), () => {
			frappe.call({
				method: 'beam.beam.printer_queue.cancel_printer_job',
				args: { server_ip, port, job_id },
				freeze: true,
				callback: () => {
					frappe.show_alert({
						message: __('Print job cancelled'),
						indicator: 'green',
					})
					this.poll_queue()
				},
			})
		})
	}
}

beam.is_printer_queue_route = function () {
	const route = frappe.get_route()
	return route[0] === 'printer-queue'
}
