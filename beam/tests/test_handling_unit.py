# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest
from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry
from erpnext.stock.stock_ledger import NegativeStockError
from erpnext.subcontracting.doctype.subcontracting_order.subcontracting_order import (
	make_subcontracting_receipt,
)

from beam.beam.scan import get_handling_unit


# utility function
def submit_all_purchase_receipts():
	for pi in frappe.get_all("Purchase Invoice", {"docstatus": 0}):
		pi = frappe.get_doc("Purchase Invoice", pi)
		pi.submit()
	for pr in frappe.get_all("Purchase Receipt", {"docstatus": 0}):
		pr = frappe.get_doc("Purchase Receipt", pr)
		pr.submit()


@pytest.mark.order(10)
def test_purchase_receipt_handling_unit_generation():
	for pr in frappe.get_all("Purchase Receipt"):
		pr = frappe.get_doc("Purchase Receipt", pr)
		for row in pr.items:
			assert row.handling_unit == None
		pr.submit()
		for row in pr.items:
			assert isinstance(row.handling_unit, str)
			if row.rejected_qty:
				assert row.rejected_qty + row.qty == row.received_qty
			hu = get_handling_unit(row.handling_unit)
			assert hu.stock_qty == row.stock_qty


@pytest.mark.order(11)
def test_purchase_invoice():
	for pi in frappe.get_all("Purchase Invoice"):
		pi = frappe.get_doc("Purchase Invoice", pi)
		for row in pi.items:
			assert row.handling_unit == None
		pi.submit()
		for row in pi.items:
			is_stock_item, enable_handling_unit = frappe.get_value(
				"Item", row.item_code, ["is_stock_item", "enable_handling_unit"]
			)
			if is_stock_item and enable_handling_unit:
				assert isinstance(row.handling_unit, str)
			else:
				assert row.handling_unit == None


@pytest.mark.order(13)
def test_stock_entry_material_receipt():
	submit_all_purchase_receipts()
	se = frappe.new_doc("Stock Entry")
	se.stock_entry_type = se.purpose = "Material Receipt"
	se.append(
		"items",
		{
			"item_code": "Ambrosia Pie",
			"qty": 15,
			"t_warehouse": "Baked Goods - APC",
			"basic_rate": frappe.get_value("Item Price", {"item_code": "Ambrosia Pie"}, "price_list_rate"),
		},
	)
	se.append(
		"items",
		{
			"item_code": "Ice Water",
			"qty": 100,
			"t_warehouse": "Refrigerator - APC",
			"basic_rate": 0,
			"allow_zero_valuation_rate": 1,
		},
	)
	se.save()
	se.submit()
	for row in se.items:
		if not frappe.get_value("Item", row.item_code, "is_stock_item") or not frappe.get_value(
			"Item", row.item_code, "enable_handling_unit"
		):
			continue

		sle = frappe.get_doc("Stock Ledger Entry", {"voucher_detail_no": row.name})
		assert row.transfer_qty == sle.actual_qty
		assert row.item_code == sle.item_code
		assert row.t_warehouse == sle.warehouse  # target warehouse
		assert row.handling_unit == sle.handling_unit


@pytest.mark.order(14)
def test_stock_entry_repack():
	submit_all_purchase_receipts()
	pr_hu = frappe.get_value(
		"Purchase Receipt Item", {"item_code": "Parchment Paper"}, "handling_unit"
	)
	pr_hu = get_handling_unit(pr_hu)
	assert pr_hu.uom == "Box"
	assert pr_hu.qty == 1
	assert pr_hu.stock_qty == 100

	se = frappe.new_doc("Stock Entry")
	se.stock_entry_type = se.purpose = "Repack"
	se.append(
		"items",
		{
			"item_code": "Parchment Paper",
			"qty": 1,
			"uom": "Box",
			"conversion_factor": 100,
			"stock_qty": 100,
			"actual_qty": 100,
			"transfer_qty": 100,
			"s_warehouse": "Storeroom - APC",
			"handling_unit": pr_hu["handling_unit"],
		},
	)
	scan = frappe.call(
		"beam.beam.scan.scan",
		**{
			"barcode": pr_hu.handling_unit,
			"context": {"frm": "Stock Entry", "doc": se.as_dict()},
			"current_qty": 100,
		},
	)
	assert scan[0]["action"] == "add_or_associate"
	se.items[0].handling_unit = scan[0]["context"].get(
		"handling_unit"
	)  # simulates the effect of 'associate'
	se.append(
		"items",
		{
			"item_code": "Parchment Paper",
			"uom": "Nos",
			"qty": 100,
			"actual_qty": 100,
			"transfer_qty": 100,
			"t_warehouse": "Storeroom - APC",
		},
	)
	se.save()
	se.submit()
	for row in se.items:
		sle = frappe.get_doc("Stock Ledger Entry", {"handling_unit": row.handling_unit})
		assert row.item_code == sle.item_code
		if row.is_finished_item:
			assert row.transfer_qty == sle.actual_qty
			assert row.t_warehouse == sle.warehouse
		else:
			assert row.transfer_qty == -(sle.actual_qty)
			assert row.s_warehouse == sle.warehouse

	hu = get_handling_unit(se.items[-1].handling_unit)
	assert hu.uom == "Nos"
	assert hu.qty == 100
	assert hu.stock_qty == 100


@pytest.mark.order(15)
def test_stock_entry_material_transfer_for_manufacture():
	submit_all_purchase_receipts()
	wo = frappe.get_value("Work Order", {"production_item": "Kaduka Key Lime Pie Filling"})
	se = make_stock_entry(wo, "Material Transfer for Manufacture", 40)
	# simulate scanning
	for row in se.get("items"):
		if not frappe.get_value("Item", row.item_code, "is_stock_item") or not frappe.get_value(
			"Item", row.item_code, "enable_handling_unit"
		):
			continue
		hu = frappe.get_value("Purchase Receipt Item", {"item_code": row.item_code}, "handling_unit")
		if not hu:
			hu = frappe.get_value("Purchase Invoice Item", {"item_code": row.item_code}, "handling_unit")
		scan = frappe.call(
			"beam.beam.scan.scan",
			**{"barcode": str(hu), "context": {"frm": "Stock Entry", "doc": se}, "current_qty": 1},
		)
		assert scan[0]["action"] == "add_or_associate"
		row["handling_unit"] = scan[0]["context"].get(
			"handling_unit"
		)  # simulates the effect of 'associate'
	_se = frappe.get_doc(**se)
	_se.save()
	_se.submit()
	for row in _se.items:
		if not frappe.get_value("Item", row.item_code, "is_stock_item") or not frappe.get_value(
			"Item", row.item_code, "enable_handling_unit"
		):
			continue
		sle = frappe.get_doc("Stock Ledger Entry", {"voucher_detail_no": row.name})
		hu = frappe.get_value(
			"Purchase Receipt Item",
			{"item_code": row.item_code},
			["item_code", "stock_qty", "handling_unit"],
			as_dict=True,
		)
		if not hu:
			hu = frappe.get_value(
				"Purchase Invoice Item",
				{"item_code": row.item_code},
				["item_code", "stock_qty", "handling_unit"],
				as_dict=True,
			)
		assert row.transfer_qty == sle.actual_qty
		assert row.item_code == sle.item_code
		assert row.t_warehouse == sle.warehouse  # target warehouse
		if hu.stock_qty != abs(sle.actual_qty):
			assert row.handling_unit != row.to_handling_unit


@pytest.mark.order(16)
def test_stock_entry_for_manufacture():
	submit_all_purchase_receipts()
	wo = frappe.get_value("Work Order", {"production_item": "Kaduka Key Lime Pie Filling"})
	se_tfm = frappe.get_value(
		"Stock Entry", {"work_order": wo, "purpose": "Material Transfer for Manufacture"}
	)
	job_cards = frappe.get_all("Job Card", {"work_order": wo})
	for job_card in job_cards:
		job_card = frappe.get_doc("Job Card", job_card)
		job_card.submit()

	se = make_stock_entry(wo, "Manufacture", 40)
	# simulate scanning
	for row in se.get("items"):
		if not frappe.get_value("Item", row.item_code, "is_stock_item") or not frappe.get_value(
			"Item", row.item_code, "enable_handling_unit"
		):
			continue
		if (
			row.is_finished_item or row.is_scrap_item
		):  # finished and scrap items' handling units will be generated and wouldn't be scanned
			continue
		hu = frappe.get_value(
			"Stock Entry Detail", {"parent": se_tfm, "item_code": row.item_code}, "to_handling_unit"
		)
		scan = frappe.call(
			"beam.beam.scan.scan",
			**{"barcode": str(hu), "context": {"frm": "Stock Entry", "doc": se}, "current_qty": 1},
		)
		# print(scan[0])
		assert scan[0]["action"] == "add_or_associate"
		row["handling_unit"] = scan[0]["context"].get(
			"handling_unit"
		)  # simulates the effect of 'associate'
	_se = frappe.get_doc(**se)
	_se.save()
	_se.submit()

	for row in _se.items:
		if not frappe.get_value("Item", row.item_code, "is_stock_item") or not frappe.get_value(
			"Item", row.item_code, "enable_handling_unit"
		):
			continue
		sle = frappe.get_doc(
			"Stock Ledger Entry", {"voucher_detail_no": row.name, "handling_unit": row.handling_unit}
		)
		if not row.is_finished_item and not row.is_scrap_item:
			assert row.transfer_qty == -(sle.actual_qty)
			assert row.item_code == sle.item_code
			assert row.s_warehouse == sle.warehouse  # source/ warehouse
			assert sle.handling_unit == row.handling_unit
		elif row.is_scrap_item:
			assert row.transfer_qty == sle.actual_qty
			assert row.item_code == sle.item_code
			create_handling_unit = frappe.get_value(
				"BOM Scrap Item", {"item_code": row.item_code, "parent": _se.bom_no}, "create_handling_unit"
			)
			if create_handling_unit:
				assert row.handling_unit == sle.handling_unit
			else:
				assert row.handling_unit == None
		else:
			assert row.transfer_qty == sle.actual_qty
			assert row.item_code == sle.item_code
			assert row.t_warehouse == sle.warehouse  # target warehouse


@pytest.mark.order(17)
def test_delivery_note():
	se = frappe.new_doc("Stock Entry")
	se.stock_entry_type = se.purpose = "Material Receipt"
	se.append(
		"items",
		{
			"item_code": "Ambrosia Pie",
			"qty": 30,
			"t_warehouse": "Baked Goods - APC",
			"basic_rate": frappe.get_value("Item Price", {"item_code": "Ambrosia Pie"}, "price_list_rate"),
		},
	)
	se.save()
	se.submit()
	handling_unit = se.items[0].handling_unit

	dn = frappe.new_doc("Delivery Note")
	dn.customer = "Almacs Food Group"
	scan = frappe.call(
		"beam.beam.scan.scan",
		**{
			"barcode": str(handling_unit),
			"context": {"frm": dn.doctype, "doc": dn.as_dict()},
			"current_qty": 1,
		},
	)
	dn.append(
		"items",
		{
			**scan[0]["context"],
			"qty": 5,
		},
	)
	dn.save()
	dn.submit()
	# assert net qty on handling unit above
	hu = get_handling_unit(handling_unit)
	assert hu.item_code == dn.items[0].item_code
	assert hu.stock_qty == 25  # 30 from stock entry less 5 from delivery note
	assert hu.item_code == dn.items[0].item_code


@pytest.mark.order(18)
def test_sales_invoice():
	se = frappe.new_doc("Stock Entry")
	se.stock_entry_type = se.purpose = "Material Receipt"
	se.append(
		"items",
		{
			"item_code": "Ambrosia Pie",
			"qty": 30,
			"t_warehouse": "Baked Goods - APC",
			"basic_rate": frappe.get_value("Item Price", {"item_code": "Ambrosia Pie"}, "price_list_rate"),
		},
	)
	se.save()
	se.submit()
	handling_unit = se.items[0].handling_unit

	si = frappe.new_doc("Sales Invoice")
	si.update_stock = 1
	si.customer = "Almacs Food Group"
	scan = frappe.call(
		"beam.beam.scan.scan",
		**{
			"barcode": str(handling_unit),
			"context": {"frm": si.doctype, "doc": si.as_dict()},
			"current_qty": 1,
		},
	)
	si.append(
		"items",
		{
			**scan[0]["context"],
			"qty": 10,
		},
	)
	si.save()
	si.submit()
	# assert net qty on handling unit above
	hu = get_handling_unit(handling_unit)
	assert hu.item_code == si.items[0].item_code
	assert hu.stock_qty == 20  # 30 from stock entry less 10 from stock entry
	assert hu.item_code == si.items[0].item_code


@pytest.mark.order(19)
def test_packing_slip():
	se = frappe.new_doc("Stock Entry")
	se.stock_entry_type = se.purpose = "Material Receipt"
	se.append(
		"items",
		{
			"item_code": "Ambrosia Pie",
			"qty": 30,
			"t_warehouse": "Baked Goods - APC",
			"basic_rate": frappe.get_value("Item Price", {"item_code": "Ambrosia Pie"}, "price_list_rate"),
		},
	)
	se.save()
	se.submit()
	handling_unit = se.items[0].handling_unit

	dn = frappe.new_doc("Delivery Note")
	dn.customer = "Beans and Dreams Roasters"
	dn.append(
		"items",
		{"item_code": "Ambrosia Pie", "qty": 30, "handling_unit": se.items[0].handling_unit},
	)
	dn.save()

	ps = frappe.new_doc("Packing Slip")
	ps.delivery_note = dn.name
	ps.from_case_no = 1
	scan = frappe.call(
		"beam.beam.scan.scan",
		**{
			"barcode": str(handling_unit),
			"context": {"frm": ps.doctype, "doc": ps.as_dict()},
			"current_qty": 1,
		},
	)
	ps.append(
		"items",
		{
			**scan[0]["context"],
		},
	)
	assert ps.items[0].dn_detail == dn.items[0].name
	ps.save()
	ps.submit()
	# assert no SL entries

	dn.submit()
	for row in dn.items:
		hu = get_handling_unit(handling_unit)
		sle = frappe.get_doc("Stock Ledger Entry", {"handling_unit": row.handling_unit})
		assert row.stock_qty == -(sle.actual_qty)
		assert row.item_code == sle.item_code
		assert row.warehouse == sle.warehouse  # target warehouse
		assert hu.stock_qty == 0


@pytest.mark.order(20)
def test_stock_entry_material_transfer():
	# create clean material receipt to avoid conflicts with Repack test
	semr = frappe.new_doc("Stock Entry")
	semr.stock_entry_type = semr.purpose = "Material Receipt"
	semr.append(
		"items",
		{
			"item_code": "Parchment Paper",
			"qty": 100,
			"t_warehouse": "Storeroom - APC",
			"basic_rate": frappe.get_value(
				"Item Price", {"item_code": "Parchment Paper"}, "price_list_rate"
			),
		},
	)
	semr.save()
	semr.submit()
	handling_unit = semr.items[0].handling_unit

	hu = get_handling_unit(handling_unit)
	assert hu.stock_qty == 100

	se = frappe.new_doc("Stock Entry")
	se.stock_entry_type = se.purpose = "Material Transfer"
	se.company = frappe.defaults.get_defaults().get("company")

	# simulate scanning
	scan = frappe.call(
		"beam.beam.scan.scan",
		**{
			"barcode": str(hu.handling_unit),
			"context": {"frm": "Stock Entry", "doc": se.as_dict()},
			"current_qty": 1,
		},
	)

	assert scan[0]["action"] == "add_or_associate"
	se.append(
		"items",
		{
			**scan[0]["context"],
			"qty": 5,
			"actual_qty": 5,
			"transfer_qty": 5,
			"s_warehouse": hu.warehouse,
			"t_warehouse": "Kitchen - APC",
		},
	)
	se.save()
	se.submit()
	for row in se.items:
		if not frappe.get_value("Item", row.item_code, "is_stock_item") or not frappe.get_value(
			"Item", row.item_code, "enable_handling_unit"
		):
			continue
		sle = frappe.get_doc("Stock Ledger Entry", {"handling_unit": row.handling_unit})
		hu = get_handling_unit(str(row.handling_unit))
		assert row.transfer_qty == abs(sle.actual_qty)
		assert hu.stock_qty == 95  # net qty
		assert row.item_code == sle.item_code == hu.item_code
		assert row.s_warehouse == sle.warehouse == hu.warehouse  # source warehouse

		tsle = frappe.get_doc("Stock Ledger Entry", {"handling_unit": row.to_handling_unit})
		hu = get_handling_unit(str(row.to_handling_unit))
		assert row.transfer_qty == abs(tsle.actual_qty)
		assert hu.stock_qty == 5
		assert row.t_warehouse == tsle.warehouse  # target warehouse

	# test how split handling units are returned
	se.cancel()
	for row in se.items:
		if not frappe.get_value("Item", row.item_code, "is_stock_item") or not frappe.get_value(
			"Item", row.item_code, "enable_handling_unit"
		):
			continue
		sle = frappe.get_doc("Stock Ledger Entry", {"handling_unit": row.handling_unit})
		hu = get_handling_unit(str(row.handling_unit))
		assert row.transfer_qty == abs(sle.actual_qty)
		assert hu.stock_qty == 95  # restored qty
		assert row.item_code == sle.item_code
		assert row.s_warehouse == sle.warehouse  # source warehouse

		tsle = frappe.get_doc("Stock Ledger Entry", {"handling_unit": row.to_handling_unit})
		hu = get_handling_unit(str(row.to_handling_unit))
		assert hu.stock_qty == 5
		assert row.t_warehouse == tsle.warehouse  # target warehouse


@pytest.mark.order(21)
def test_stock_entry_for_send_to_subcontractor():
	submit_all_purchase_receipts()
	se = frappe.new_doc("Stock Entry")
	se.stock_entry_type = se.purpose = "Send to Subcontractor"

	hu = frappe.get_value("Purchase Invoice Item", {"item_code": "Flour"}, "handling_unit")
	# simulate scanning
	scan = frappe.call(
		"beam.beam.scan.scan",
		**{"barcode": str(hu), "context": {"frm": "Stock Entry", "doc": se.as_dict()}, "current_qty": 1},
	)
	assert scan[0]["action"] == "add_or_associate"
	se.append(
		"items",
		{
			**scan[0]["context"],
			"qty": 30,
			"s_warehouse": "Storeroom - APC",
			"t_warehouse": "Kitchen - APC",
		},
	)
	se.save()
	for row in se.items:
		if not frappe.get_value("Item", row.item_code, "is_stock_item") or not frappe.get_value(
			"Item", row.item_code, "enable_handling_unit"
		):
			continue
		sle = frappe.get_doc("Stock Ledger Entry", {"handling_unit": row.handling_unit})
		assert row.item_code == sle.item_code
		assert row.s_warehouse == sle.warehouse  # source warehouse

	se.submit()
	for row in se.items:
		if not frappe.get_value("Item", row.item_code, "is_stock_item") or not frappe.get_value(
			"Item", row.item_code, "enable_handling_unit"
		):
			continue
		sle = frappe.get_doc("Stock Ledger Entry", {"handling_unit": row.handling_unit})
		assert row.transfer_qty == abs(sle.actual_qty)
		assert row.item_code == sle.item_code
		hu = get_handling_unit(row.handling_unit)
		_hu = get_handling_unit(row.to_handling_unit)
		sle = frappe.get_doc("Stock Ledger Entry", {"handling_unit": row.handling_unit})
		assert hu.stock_qty == 55  # net quantity; 85 - 30
		assert row.transfer_qty == abs(sle.actual_qty)
		assert row.item_code == sle.item_code
		assert row.s_warehouse == sle.warehouse  # source warehouse

		tsle = frappe.get_doc("Stock Ledger Entry", {"handling_unit": row.to_handling_unit})
		assert _hu.stock_qty == 30
		assert row.transfer_qty == abs(tsle.actual_qty)
		assert row.item_code == tsle.item_code
		assert row.t_warehouse == tsle.warehouse  # target warehouse

	se.cancel()
	for row in se.items:
		hu = get_handling_unit(row.to_handling_unit)
		assert hu.qty > 0


@pytest.mark.order(22)
def test_subcontracting_receipt():
	for row in frappe.get_all("Subcontracting Order", pluck="name"):
		if not frappe.db.exists(
			"Subcontracting Receipt Item", {"docstatus": 1, "subcontracting_order": row}
		):
			so_doc = make_subcontracting_receipt(row)
			so_doc.save()

	for sr in frappe.get_all("Subcontracting Receipt"):
		sr = frappe.get_doc("Subcontracting Receipt", sr)
		for row in sr.items:
			assert row.handling_unit == None
		sr.submit()
		for row in sr.items:
			assert isinstance(row.handling_unit, str)
			if row.rejected_qty:
				assert row.rejected_qty + row.qty == row.received_qty
				hu = get_handling_unit(row.handling_unit)
				assert hu.stock_qty == row.returned_qty


@pytest.mark.order(23)
@pytest.mark.skip()  # Remove when validate_handling_unit_overconsumption is uncommented in hooks.py doc_events
def test_handling_units_overconsumption_in_material_transfer_stock_entry():
	# Tests validate_handling_unit_overconsumption Stock Entry incoming code block
	with pytest.raises(NegativeStockError) as exc_info:
		se = frappe.new_doc("Stock Entry")
		se.stock_entry_type = se.purpose = "Material Receipt"
		se.append(
			"items",
			{
				"item_code": "Butter",
				"qty": 5,
				"t_warehouse": "Refrigerator - APC",
				"basic_rate": frappe.get_value("Item Price", {"item_code": "Butter"}, "price_list_rate"),
			},
		)
		se.save()
		se.submit()
		handling_unit_1 = se.items[0].handling_unit

		hu_1 = get_handling_unit(handling_unit_1)
		assert hu_1.stock_qty == 5

		se = frappe.new_doc("Stock Entry")
		se.stock_entry_type = se.purpose = "Material Issue"
		scan = frappe.call(
			"beam.beam.scan.scan",
			**{
				"barcode": str(handling_unit_1),
				"context": {"frm": se.doctype, "doc": se.as_dict()},
				"current_qty": 1,
			},
		)
		se.append(
			"items",
			{
				**scan[0]["context"],
			},
		)

		assert se.items[0].qty == 5

		se.items[0].s_warehouse = "Refrigerator - APC"
		se.items[0].qty = 8
		se.items[0].actual_qty = 8
		se.items[0].transfer_qty = 8
		row_qty = se.items[0].transfer_qty
		row_stock_uom = se.items[0].stock_uom
		se.save()

	assert (
		f"Row #1: Handling Unit for Butter cannot be more than {hu_1.stock_qty:.1f} {hu_1.stock_uom}. You have {row_qty:.1f} {row_stock_uom}"
		in exc_info.value.args[0]
	)


@pytest.mark.order(24)
@pytest.mark.skip()  # Remove when validate_handling_unit_overconsumption is uncommented in hooks.py doc_events
def test_handling_units_overconsumption_in_delivery_note():
	# Tests validate_handling_unit_overconsumption Delivery Note code block
	with pytest.raises(NegativeStockError) as exc_info:
		se = frappe.new_doc("Stock Entry")
		se.stock_entry_type = se.purpose = "Material Receipt"
		se.append(
			"items",
			{
				"item_code": "Ambrosia Pie",
				"qty": 30,
				"t_warehouse": "Baked Goods - APC",
				"basic_rate": frappe.get_value("Item Price", {"item_code": "Ambrosia Pie"}, "price_list_rate"),
			},
		)
		se.save()
		se.submit()
		handling_unit = se.items[0].handling_unit
		hu = get_handling_unit(handling_unit)

		dn = frappe.new_doc("Delivery Note")
		dn.customer = "Almacs Food Group"
		scan = frappe.call(
			"beam.beam.scan.scan",
			**{
				"barcode": str(handling_unit),
				"context": {"frm": dn.doctype, "doc": dn.as_dict()},
				"current_qty": 1,
			},
		)
		dn.append(
			"items",
			{
				**scan[0]["context"],
				"qty": 35,
			},
		)
		row_qty = dn.get("items")[0].qty
		row_stock_uom = dn.get("items")[0].stock_uom
		dn.save()

	assert (
		f"Row #1: Handling Unit for Ambrosia Pie cannot be more than {hu.stock_qty} {hu.stock_uom}. You have {row_qty:.1f} {row_stock_uom}"
		in exc_info.value.args[0]
	)
