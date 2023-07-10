import frappe
import pytest
from erpnext.manufacturing.doctype.work_order.work_order import make_stock_entry

from beam.beam.scan import get_handling_unit


# utility function
def submit_all_purchase_receipts():
	for pi in frappe.get_all("Purchase Invoice", {"docstatus": 0}):
		pi = frappe.get_doc("Purchase Invoice", pi)
		pi.submit()
	for pr in frappe.get_all("Purchase Receipt", {"docstatus": 0}):
		pr = frappe.get_doc("Purchase Receipt", pr)
		pr.submit()


def test_purchase_receipt_handling_unit_generation():
	for pr in frappe.get_all("Purchase Receipt"):
		pr = frappe.get_doc("Purchase Receipt", pr)
		for row in pr.items:
			assert row.handling_unit == None
		pr.submit()
		for row in pr.items:
			assert isinstance(row.handling_unit, str)


def test_purchase_invoice():
	for pi in frappe.get_all("Purchase Invoice"):
		pi = frappe.get_doc("Purchase Invoice", pi)
		for row in pi.items:
			assert row.handling_unit == None
		pi.submit()
		for row in pi.items:
			if frappe.get_value("Item", row.item_code, "is_stock_item"):
				assert isinstance(row.handling_unit, str)
			else:
				assert row.handling_unit == None


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
			"qty": 1000000000,
			"t_warehouse": "Refrigerator - APC",
			"basic_rate": 0,
			"allow_zero_valuation_rate": 1,
		},
	)
	se.save()
	se.submit()
	for row in se.items:
		if not frappe.get_value("Item", row.item_code, "is_stock_item"):
			continue

		sle = frappe.get_doc("Stock Ledger Entry", {"handling_unit": row.handling_unit})
		assert row.transfer_qty == sle.actual_qty  # AKA stock_qty in every other doctype
		assert row.item_code == sle.item_code
		assert row.t_warehouse == sle.warehouse  # target warehouse


def test_stock_entry_repack():
	submit_all_purchase_receipts()
	pr_hu = frappe.get_value(
		"Purchase Receipt Item", {"item_code": "Parchment Paper"}, "handling_unit"
	)
	pr_hu = get_handling_unit(pr_hu)
	assert pr_hu.uom == "Box"
	assert pr_hu.stock_qty == 1

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
			"s_warehouse": "Storeroom - APC",
		},
	)
	se.append(
		"items",
		{
			"item_code": "Parchment Paper",
			"uom": "Nos",
			"qty": 100,
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
	assert hu.stock_qty == 100


def test_stock_entry_material_transfer():
	submit_all_purchase_receipts()
	se = frappe.new_doc("Stock Entry")
	se.stock_entry_type = se.purpose = "Material Transfer"

	hu = frappe.get_value("Purchase Receipt Item", {"item_code": "Cocoplum"}, "handling_unit")
	# simulate scanning
	scan = frappe.call(
		"beam.beam.scan.scan",
		**{"barcode": str(hu), "context": {"frm": "Stock Entry", "doc": se.as_dict()}, "current_qty": 1}
	)
	assert scan[0]["action"] == "add_or_associate"
	se.append(
		"items",
		{
			**scan[0]["context"],
			"qty": 30,
			"s_warehouse": "Refrigerator - APC",
			"t_warehouse": "Kitchen - APC",
		},
	)
	se.save()

	for row in se.items:
		if not frappe.get_value("Item", row.item_code, "is_stock_item"):
			continue
		sle = frappe.get_doc("Stock Ledger Entry", {"handling_unit": row.handling_unit})
		assert row.item_code == sle.item_code
		assert row.s_warehouse == sle.warehouse  # source warehouse

	se.submit()
	for row in se.items:
		if not frappe.get_value("Item", row.item_code, "is_stock_item"):
			continue
		sle = frappe.get_doc("Stock Ledger Entry", {"handling_unit": row.handling_unit})
		assert row.transfer_qty == sle.actual_qty  # AKA stock_qty in every other doctype
		assert row.item_code == sle.item_code
		assert row.t_warehouse == sle.warehouse  # target warehouse

	se.cancel()  # undo so it this doesn't effect downstream transactions


def test_stock_entry_material_transfer_for_manufacture():
	submit_all_purchase_receipts()
	wo = frappe.get_value("Work Order", {"production_item": "Kaduka Key Lime Pie Filling"})
	se = make_stock_entry(wo, "Material Transfer for Manufacture", 40)
	# simulate scanning
	for row in se.get("items"):
		hu = frappe.get_value("Purchase Receipt Item", {"item_code": row.item_code}, "handling_unit")
		if not hu:
			hu = frappe.get_value("Purchase Invoice Item", {"item_code": row.item_code}, "handling_unit")
		scan = frappe.call(
			"beam.beam.scan.scan",
			**{"barcode": str(hu), "context": {"frm": "Stock Entry", "doc": se}, "current_qty": 1}
		)
		assert scan[0]["action"] == "add_or_associate"
		row["handling_unit"] = scan[0]["context"].get(
			"handling_unit"
		)  # simulates the effect of 'associate'
	_se = frappe.get_doc(**se)
	_se.save()
	for row in _se.items:
		if not frappe.get_value("Item", row.item_code, "is_stock_item"):
			continue
		sle = frappe.get_doc("Stock Ledger Entry", {"handling_unit": row.handling_unit})
		assert row.item_code == sle.item_code
		assert row.s_warehouse == sle.warehouse  # source warehouse

	_se.submit()
	for row in _se.items:
		if not frappe.get_value("Item", row.item_code, "is_stock_item"):
			continue
		sle = frappe.get_doc("Stock Ledger Entry", {"handling_unit": row.handling_unit})
		assert row.transfer_qty == sle.actual_qty  # AKA stock_qty in every other doctype
		assert row.item_code == sle.item_code
		assert row.t_warehouse == sle.warehouse  # target warehouse


def test_stock_entry_for_manufacture():
	submit_all_purchase_receipts()
	wo = frappe.get_value("Work Order", {"production_item": "Kaduka Key Lime Pie Filling"})
	se = make_stock_entry(wo, "Manufacture", 40)
	# simulate scanning
	for row in se.get("items"):
		if row.is_finished_item:  # finished item handling unit will be generated and wouldn't be scanned
			continue
		hu = frappe.get_value("Purchase Receipt Item", {"item_code": row.item_code}, "handling_unit")
		if not hu:
			hu = frappe.get_value("Purchase Invoice Item", {"item_code": row.item_code}, "handling_unit")
		scan = frappe.call(
			"beam.beam.scan.scan",
			**{"barcode": str(hu), "context": {"frm": "Stock Entry", "doc": se}, "current_qty": 1}
		)
		assert scan[0]["action"] == "add_or_associate"
		row["handling_unit"] = scan[0]["context"].get(
			"handling_unit"
		)  # simulates the effect of 'associate'
	_se = frappe.get_doc(**se)
	_se.save()
	_se.submit()

	for row in _se.items:
		if not frappe.get_value("Item", row.item_code, "is_stock_item"):
			continue
		sle = frappe.get_doc("Stock Ledger Entry", {"handling_unit": row.handling_unit})
		if not row.is_finished_item:
			assert row.transfer_qty == -(sle.actual_qty)  # AKA stock_qty in every other doctype
			assert row.item_code == sle.item_code
			assert row.s_warehouse == sle.warehouse  # target warehouse
		else:
			assert row.transfer_qty == sle.actual_qty  # AKA stock_qty in every other doctype
			assert row.item_code == sle.item_code
			assert row.t_warehouse == sle.warehouse  # target warehouse


@pytest.mark.skip()
def test_stock_entry_for_manufacture_with_optional_scrap():
	pass


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
		}
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
		}
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
		}
	)
	ps.append(
		"items",
		{
			**scan[0]["context"],
		},
	)
	ps.save()
	ps.submit()
	# assert no SL entries

	dn.submit()
	for row in dn.items:
		hu = get_handling_unit(handling_unit)
		sle = frappe.get_doc("Stock Ledger Entry", {"handling_unit": row.handling_unit})
		assert row.stock_qty == -(sle.actual_qty)  # AKA stock_qty in every other doctype
		assert row.item_code == sle.item_code
		assert row.warehouse == sle.warehouse  # target warehouse
		assert hu.stock_qty == 0


def test_test_stock_entry_for_send_to_subcontractor():
	submit_all_purchase_receipts()
	se = frappe.new_doc("Stock Entry")
	se.stock_entry_type = se.purpose = "Send to Subcontractor"

	hu = frappe.get_value("Purchase Invoice Item", {"item_code": "Flour"}, "handling_unit")
	# simulate scanning
	scan = frappe.call(
		"beam.beam.scan.scan",
		**{"barcode": str(hu), "context": {"frm": "Stock Entry", "doc": se.as_dict()}, "current_qty": 1}
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
		if not frappe.get_value("Item", row.item_code, "is_stock_item"):
			continue
		sle = frappe.get_doc("Stock Ledger Entry", {"handling_unit": row.handling_unit})
		assert row.item_code == sle.item_code
		assert row.s_warehouse == sle.warehouse  # source warehouse

	se.submit()
	for row in se.items:
		if not frappe.get_value("Item", row.item_code, "is_stock_item"):
			continue
		sle = frappe.get_doc("Stock Ledger Entry", {"handling_unit": row.handling_unit})
		assert -(row.transfer_qty) == sle.actual_qty
		assert row.item_code == sle.item_code
		assert row.s_warehouse == sle.warehouse  # source warehouse
		hu = get_handling_unit(row.handling_unit)
		assert hu.stock_qty == 55  # net quantity; 85 - 30

		sle = frappe.get_doc(
			"Stock Ledger Entry", {"handling_unit": row.to_handling_unit}
		)  # target handling unit
		assert row.transfer_qty == sle.actual_qty
		assert row.item_code == sle.item_code
		assert row.t_warehouse == sle.warehouse  # target warehouse

		hu = get_handling_unit(row.to_handling_unit)
		assert hu.stock_qty == 30

	se.cancel()


@pytest.mark.skip()
def test_subcontracting():
	# Use pie crust
	# create purchase order
	# create subcontracting
	# create and test generation of handling units on subcontracting receipt
	pass
