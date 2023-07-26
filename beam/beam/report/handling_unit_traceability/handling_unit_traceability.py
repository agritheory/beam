# Copyright (c) 2023, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.query_builder import DocType


def get_stock_ledger_entries_hu(handling_unit):
	stock_ledger_entry = DocType("Stock Ledger Entry")
	return (
		frappe.qb.from_(stock_ledger_entry)
		.select(
			stock_ledger_entry.name,
			stock_ledger_entry.creation,
			stock_ledger_entry.company,
			stock_ledger_entry.voucher_type,
			stock_ledger_entry.voucher_no,
			stock_ledger_entry.voucher_detail_no,
			stock_ledger_entry.handling_unit,
			stock_ledger_entry.warehouse,
			stock_ledger_entry.actual_qty,
			stock_ledger_entry.item_code,
		)
		.where(stock_ledger_entry.handling_unit == handling_unit)
		.orderby("creation", frappe.qb.desc)
	).run(as_dict=True)


def execute(filters=None):
	if not any([filters.handling_unit, filters.delivery_note, filters.sales_invoice]):
		return

	data = []
	work_orders = {}

	if filters.delivery_note:
		handling_units = frappe.get_all(
			"Delivery Note Item", filters={"parent": filters.delivery_note}, pluck="handling_unit"
		)

	if filters.sales_invoice:
		handling_units = frappe.get_all(
			"Sales Invoice Item", filters={"parent": filters.sales_invoice}, pluck="handling_unit"
		)

	if filters.handling_unit:
		handling_units = [filters.handling_unit]

	for handling_unit in handling_units:

		results = get_stock_ledger_entries_hu(handling_unit)

		hu_results = []
		hu_results += results

		for result in results:
			if result["voucher_type"] != "Stock Entry":
				continue

			previous_handling_units = frappe.get_all(
				"Stock Entry Detail",
				filters={"parent": result["voucher_no"], "handling_unit": ("not in", handling_unit)},
				pluck="handling_unit",
			)

			for previous_handling_unit in previous_handling_units:
				previous_stock_entries = get_stock_ledger_entries_hu(previous_handling_unit)
				hu_results += previous_stock_entries

				for previous_stock_entry in previous_stock_entries:
					if previous_stock_entry["voucher_type"] != "Stock Entry":
						continue

					work_order_name = frappe.db.get_value(
						previous_stock_entry["voucher_type"], previous_stock_entry["voucher_no"], "work_order"
					)
					if work_order_name:
						work_order = frappe.get_doc("Work Order", work_order_name)
						if work_order.name not in work_orders:
							work_orders[work_order.name] = hu_results

	for work_order, rows in work_orders.items():

		rows = sorted(rows, key=lambda r: r["creation"])
		data.append({"indent": 0, "work_order": work_order})

		for row in rows:
			row["indent"] = 1
			data.append(row)

	return get_columns(), data


def get_columns():
	return [
		{
			"label": _("Work Order"),
			"fieldname": "work_order",
			"fieldtype": "Link",
			"options": "Work Order",
			"width": 220,
		},
		{"label": _("Voucher Type"), "fieldname": "voucher_type", "fieldtype": "Data", "width": 150},
		{
			"label": _("Voucher No"),
			"fieldname": "voucher_no",
			"fieldtype": "Dynamic Link",
			"options": "voucher_type",
			"width": 180,
		},
		# {
		# 	"label": _("Stock Ledger Entry"),
		# 	"fieldname": "name",
		# 	"fieldtype": 'Link',
		# 	'options': "Stock Ledger Entry",
		# 	"width": 180
		# },
		{
			"label": _("Item Code"),
			"fieldname": "item_code",
			"fieldtype": "Link",
			"options": "Item",
			"width": 120,
		},
		{
			"label": _("Qty"),
			"fieldname": "actual_qty",
			"fieldtype": "Data",
			"width": 50,
		},
		{
			"label": _("Warehouse"),
			"fieldname": "warehouse",
			"fieldtype": "Link",
			"options": "Warehouse",
			"width": 180,
		},
		{
			"label": _("Handling Unit"),
			"fieldname": "handling_unit",
			"fieldtype": "Link",
			"options": "Handling Unit",
			"width": 200,
		},
	]
