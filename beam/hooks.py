app_name = "beam"
app_title = "BEAM"
app_publisher = "AgriTheory"
app_description = "Barcode Scanning for ERPNext"
app_email = "support@agritheory.dev"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/beam/css/beam.css"
app_include_js = ["beam.bundle.js"]

# include js, css files in header of web template
# web_include_css = "/assets/beam/css/beam.css"
web_include_js = ["beam-web.bundle.js"]

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "beam/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {"Stock Entry": "public/js/stock_entry_custom.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Jinja
# ----------

jinja = {
	"methods": [
		"beam.beam.scan.get_handling_unit",
		"beam.beam.barcodes.barcode128",
	]
}

# Installation
# ------------

# before_install = "beam.install.before_install"
after_install = "beam.install.after_install"
after_migrate = "beam.install.after_install"

# Uninstallation
# ------------

# before_uninstall = "beam.uninstall.before_uninstall"
# after_uninstall = "beam.uninstall.after_uninstall"

# Boot
extend_bootinfo = "beam.beam.boot.boot_session"


# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "beam.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# DocType Class
# ---------------
# Override standard doctype classes
override_doctype_class = {
	"Sales Order": "beam.beam.overrides.sales_order.BEAMSalesOrder",
	"Stock Entry": "beam.beam.overrides.stock_entry.BEAMStockEntry",
	"Subcontracting Receipt": "beam.beam.overrides.subcontracting_receipt.BEAMSubcontractingReceipt",
	"Work Order": "beam.beam.overrides.work_order.BEAMWorkOrder",
}


# Document Events
# ---------------
# Hook on document methods and events

doc_events = {
	("Item", "Warehouse"): {
		"validate": ["beam.beam.barcodes.create_beam_barcode"],
	},
	# (
	# 	"Purchase Receipt",
	# 	"Stock Entry",
	# 	"Sales Invoice",
	# 	"Delivery Note",
	# ): {"validate": ["beam.beam.handling_unit.validate_handling_unit_overconsumption"]},
	(
		"Delivery Note",
		"Purchase Invoice",
		"Purchase Receipt",
		"Sales Invoice",
		"Stock Entry",
		"Stock Reconciliation",
	): {
		"on_submit": ["beam.beam.demand.demand.modify_allocations"],
		"on_cancel": ["beam.beam.demand.demand.modify_allocations"],
	},
	("Purchase Receipt", "Purchase Invoice", "Subcontracting Receipt"): {
		"before_submit": ["beam.beam.handling_unit.generate_handling_units"],
	},
	"Stock Entry": {
		"before_submit": [
			"beam.beam.handling_unit.generate_handling_units",
			"beam.beam.overrides.stock_entry.validate_items_with_handling_unit",
		],
	},
	("Sales Order", "Work Order"): {
		"on_submit": ["beam.beam.demand.demand.modify_demand"],
		"on_cancel": ["beam.beam.demand.demand.modify_demand"],
	},
}

# Scheduled Tasks
# ---------------

# scheduler_events = {
# 	"all": [
# 		"beam.tasks.all"
# 	],
# 	"daily": [
# 		"beam.tasks.daily"
# 	],
# 	"hourly": [
# 		"beam.tasks.hourly"
# 	],
# 	"weekly": [
# 		"beam.tasks.weekly"
# 	],
# 	"monthly": [
# 		"beam.tasks.monthly"
# 	],
# }

# Testing
# -------

# before_tests = "beam.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "beam.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "beam.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["beam.utils.before_request"]
# after_request = ["beam.utils.after_request"]

# Job Events
# ----------
# before_job = ["beam.utils.before_job"]
# after_job = ["beam.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"beam.auth.validate"
# ]

demand = {
	"Delivery Note": {
		"on_submit": [
			{"warehouse_field": "warehouse", "quantity_field": "stock_qty", "demand_effect": "increase"}
		],
		"on_cancel": [
			{"warehouse_field": "warehouse", "quantity_field": "stock_qty", "demand_effect": "decrease"}
		],
	},
	"Purchase Invoice": {
		"on_submit": [
			{
				"warehouse_field": "warehouse",
				"quantity_field": "stock_qty",
				"demand_effect": "decrease",
				"conditions": {"is_return": False},
			},
			{
				"warehouse_field": "warehouse",
				"quantity_field": "stock_qty",
				"demand_effect": "increase",
				"conditions": {"is_return": True},
			},
		],
		"on_cancel": [
			{
				"warehouse_field": "warehouse",
				"quantity_field": "stock_qty",
				"demand_effect": "increase",
				"conditions": {"is_return": False},
			},
			{
				"warehouse_field": "warehouse",
				"quantity_field": "stock_qty",
				"demand_effect": "decrease",
				"conditions": {"is_return": True},
			},
		],
	},
	"Purchase Receipt": {
		"on_submit": [
			{"warehouse_field": "warehouse", "quantity_field": "stock_qty", "demand_effect": "increase"}
		],
		"on_cancel": [
			{"warehouse_field": "warehouse", "quantity_field": "stock_qty", "demand_effect": "decrease"}
		],
	},
	"Sales Invoice": {
		"on_submit": [
			{
				"warehouse_field": "warehouse",
				"quantity_field": "stock_qty",
				"demand_effect": "increase",
				"conditions": {"is_return": False},
			},
			{
				"warehouse_field": "warehouse",
				"quantity_field": "stock_qty",
				"demand_effect": "decrease",
				"conditions": {"is_return": True},
			},
		],
		"on_cancel": [
			{
				"warehouse_field": "warehouse",
				"quantity_field": "stock_qty",
				"demand_effect": "decrease",
				"conditions": {"is_return": False},
			},
			{
				"warehouse_field": "warehouse",
				"quantity_field": "stock_qty",
				"demand_effect": "increase",
				"conditions": {"is_return": True},
			},
		],
	},
	"Stock Entry": {
		"on_submit": [
			{
				"warehouse_field": "s_warehouse",
				"quantity_field": "transfer_qty",
				"demand_effect": "decrease",
				"conditions": {"purpose": "Material Transfer for Manufacture"},
			},
			{
				"warehouse_field": "t_warehouse",
				"quantity_field": "transfer_qty",
				"demand_effect": "increase",
				"conditions": {"purpose": "Material Transfer for Manufacture"},
			},
			{
				"warehouse_field": "s_warehouse",
				"quantity_field": "transfer_qty",
				"demand_effect": "decrease",
				"conditions": {"purpose": "Material Issue"},
			},
			{
				"warehouse_field": "t_warehouse",
				"quantity_field": "transfer_qty",
				"demand_effect": "increase",
				"conditions": {"purpose": "Material Receipt"},
			},
			{
				"warehouse_field": "s_warehouse",
				"quantity_field": "transfer_qty",
				"demand_effect": "decrease",
				"conditions": {"purpose": "Material Transfer"},
			},
			{
				"warehouse_field": "t_warehouse",
				"quantity_field": "transfer_qty",
				"demand_effect": "increase",
				"conditions": {"purpose": "Material Transfer"},
			},
			{
				"warehouse_field": "s_warehouse",
				"quantity_field": "transfer_qty",
				"demand_effect": "decrease",
				"conditions": {"purpose": "Manufacture"},
			},
			{
				"warehouse_field": "t_warehouse",
				"quantity_field": "transfer_qty",
				"demand_effect": "increase",
				"conditions": {"purpose": "Manufacture"},
			},
			{
				"warehouse_field": "s_warehouse",
				"quantity_field": "transfer_qty",
				"demand_effect": "decrease",
				"conditions": {"purpose": "Repack"},
			},
			{
				"warehouse_field": "t_warehouse",
				"quantity_field": "transfer_qty",
				"demand_effect": "increase",
				"conditions": {"purpose": "Repack"},
			},
			{
				"warehouse_field": "s_warehouse",
				"quantity_field": "transfer_qty",
				"demand_effect": "decrease",
				"conditions": {"purpose": "Send to Subcontractor"},
			},
			{
				"warehouse_field": "t_warehouse",
				"quantity_field": "transfer_qty",
				"demand_effect": "increase",
				"conditions": {"purpose": "Send to Subcontractor"},
			},
		],
		"on_cancel": [
			{
				"warehouse_field": "s_warehouse",
				"quantity_field": "transfer_qty",
				"demand_effect": "increase",
				"conditions": {"purpose": "Material Transfer for Manufacture"},
			},
			{
				"warehouse_field": "t_warehouse",
				"quantity_field": "transfer_qty",
				"demand_effect": "decrease",
				"conditions": {"purpose": "Material Transfer for Manufacture"},
			},
			{
				"warehouse_field": "s_warehouse",
				"quantity_field": "transfer_qty",
				"demand_effect": "increase",
				"conditions": {"purpose": "Material Issue"},
			},
			{
				"warehouse_field": "s_warehouse",
				"quantity_field": "transfer_qty",
				"demand_effect": "decrease",
				"conditions": {"purpose": "Material Receipt"},
			},
			{
				"warehouse_field": "s_warehouse",
				"quantity_field": "transfer_qty",
				"demand_effect": "increase",
				"conditions": {"purpose": "Material Transfer"},
			},
			{
				"warehouse_field": "t_warehouse",
				"quantity_field": "transfer_qty",
				"demand_effect": "decrease",
				"conditions": {"purpose": "Material Transfer"},
			},
			{
				"warehouse_field": "s_warehouse",
				"quantity_field": "transfer_qty",
				"demand_effect": "increase",
				"conditions": {"purpose": "Manufacture"},
			},
			{
				"warehouse_field": "t_warehouse",
				"quantity_field": "transfer_qty",
				"demand_effect": "decrease",
				"conditions": {"purpose": "Manufacture"},
			},
			{
				"warehouse_field": "s_warehouse",
				"quantity_field": "transfer_qty",
				"demand_effect": "increase",
				"conditions": {"purpose": "Repack"},
			},
			{
				"warehouse_field": "t_warehouse",
				"quantity_field": "transfer_qty",
				"demand_effect": "decrease",
				"conditions": {"purpose": "Repack"},
			},
			{
				"warehouse_field": "s_warehouse",
				"quantity_field": "transfer_qty",
				"demand_effect": "increase",
				"conditions": {"purpose": "Send to Subcontractor"},
			},
			{
				"warehouse_field": "t_warehouse",
				"quantity_field": "transfer_qty",
				"demand_effect": "decrease",
				"conditions": {"purpose": "Send to Subcontractor"},
			},
		],
	},
	"Stock Reconciliation": {
		"on_submit": [
			{"warehouse_field": "warehouse", "quantity_field": "qty", "demand_effect": "adjustment"}
		],
		"on_cancel": [
			{"warehouse_field": "warehouse", "quantity_field": "qty", "demand_effect": "adjustment"}
		],
	},
}
