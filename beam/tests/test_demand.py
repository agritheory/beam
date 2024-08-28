# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import random
from pathlib import Path

import frappe
import pytest
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
from frappe.utils import add_days, get_site_path, today

from beam.beam.demand.demand import build_demand_allocation_map, get_demand
from beam.tests.fixtures import customers

# TODO:
# configure rejected warehouse and make sure its under test for demand
# debug allocation issues when
# add filters to Demand Map: manufactured items, purchased items, finished goods


@pytest.mark.order(1)
def test_opening_demand():
	# destroy and reset
	demand_db_path = Path(f"{get_site_path()}/demand.db").resolve()
	if demand_db_path.exists():
		demand_db_path.unlink(missing_ok=True)

	build_demand_allocation_map()
	# get demand assert that correct quantities and allocations exist
	water = get_demand(item_code="Water")
	assert len(water) == 4

	assert water[0].total_required_qty == 10.0
	assert water[0].net_required_qty == 1.0
	assert water[0].allocated_qty == 9.0
	assert water[0].warehouse == "Refrigerator - APC"
	assert water[0].parent == "MFG-WO-2024-00006"

	assert water[1].total_required_qty == 2.5
	assert water[1].net_required_qty == 2.5
	assert water[1].allocated_qty == 0.0
	assert water[1].warehouse == "Kitchen - APC"
	assert water[1].parent == "MFG-WO-2024-00007"

	assert water[2].total_required_qty == 2.5
	assert water[2].net_required_qty == 2.5
	assert water[2].allocated_qty == 0
	assert water[2].warehouse == "Kitchen - APC"
	assert water[2].parent == "MFG-WO-2024-00008"

	assert water[3].total_required_qty == 10.0
	assert water[3].net_required_qty == 10.0
	assert water[3].allocated_qty == 0.0
	assert water[3].warehouse == "Kitchen - APC"
	assert water[3].parent == "MFG-WO-2024-00009"

	ice_water = get_demand(item_code="Ice Water")
	assert len(ice_water) == 1

	assert ice_water[0].total_required_qty == 50
	assert ice_water[0].net_required_qty == 39
	assert ice_water[0].allocated_qty == 11
	assert ice_water[0].warehouse == "Refrigerator - APC"
	assert ice_water[0].parent == "MFG-WO-2024-00005"


@pytest.mark.order(2)
def test_insufficient_total_demand_scenario():
	# test multiple allocations
	se = frappe.new_doc("Stock Entry")
	se.stock_entry_type = se.purpose = "Material Receipt"
	se.append(
		"items",
		{
			"item_code": "Water",
			"qty": 7,
			"t_warehouse": "Refrigerator - APC",
			"uom": "Cup",
			"basic_rate": 0.15,
			"expense_account": "5111 - Cost of Goods Sold - APC",
		},
	)
	se.append(
		"items",
		{
			"item_code": "Ice Water",
			"qty": 100,
			"uom": "Cup",
			"t_warehouse": "Refrigerator - APC",
			"basic_rate": 0.30,
			"expense_account": "5111 - Cost of Goods Sold - APC",
		},
	)
	se.save()
	se.submit()
	water = get_demand(item_code="Water")
	assert len(water) == 4

	assert water[0].total_required_qty == 10
	assert water[0].net_required_qty == 0.0
	assert water[0].allocated_qty == 10.0
	assert water[0].warehouse == "Refrigerator - APC"
	assert water[0].parent == "MFG-WO-2024-00006"

	assert water[1].total_required_qty == 2.5
	assert water[1].net_required_qty == 2.5
	assert water[1].allocated_qty == 0.0
	assert water[1].warehouse == "Kitchen - APC"
	assert water[1].parent == "MFG-WO-2024-00007"

	assert water[2].total_required_qty == 2.5
	assert water[2].net_required_qty == 2.5
	assert water[2].allocated_qty == 0
	assert water[2].warehouse == "Kitchen - APC"
	assert water[2].parent == "MFG-WO-2024-00008"

	assert water[3].total_required_qty == 10.0
	assert water[3].net_required_qty == 10.0
	assert water[3].allocated_qty == 0.0
	assert water[3].warehouse == "Kitchen - APC"
	assert water[3].parent == "MFG-WO-2024-00009"

	# assert partial allocations
	ice_water = get_demand(item_code="Ice Water")
	assert len(ice_water) == 1

	assert ice_water[0].total_required_qty == 50
	assert ice_water[0].net_required_qty == 0
	assert ice_water[0].allocated_qty == 50
	assert ice_water[0].warehouse == "Refrigerator - APC"
	assert ice_water[0].parent == "MFG-WO-2024-00005"


@pytest.mark.order(3)
def test_demand_removal_on_order_cancel():
	pie = get_demand(item_code="Ambrosia Pie")
	assert len(pie) == 1

	so = frappe.new_doc("Sales Order")
	so.customer = random.choice(customers)
	so.selling_price_list = "Bakery Wholesale"
	so.append(
		"items",
		{
			"item_code": "Ambrosia Pie",
			"delivery_date": add_days(today(), 7),
			"qty": 10,
			"warehouse": "Baked Goods - APC",
		},
	)
	so.save()
	so.submit()

	pie = get_demand(item_code="Ambrosia Pie")
	assert len(pie) == 2

	so.cancel()
	so.delete()

	pie = get_demand(item_code="Ambrosia Pie")
	assert len(pie) == 1


@pytest.mark.order(4)
def test_allocation_creation_on_delivery():
	se = frappe.new_doc("Stock Entry")
	se.stock_entry_type = se.purpose = "Material Receipt"
	se.append(
		"items",
		{
			"item_code": "Ambrosia Pie",
			"qty": 40,
			"t_warehouse": "Baked Goods - APC",
			"basic_rate": frappe.get_value("Item Price", {"item_code": "Ambrosia Pie"}, "price_list_rate"),
		},
	)
	se.save()
	se.submit()

	# assert partial allocations
	pie = get_demand(item_code="Ambrosia Pie")
	assert len(pie) == 1

	assert pie[0].total_required_qty == 40
	assert pie[0].net_required_qty == 0
	assert pie[0].allocated_qty == 40
	assert pie[0].warehouse == "Baked Goods - APC"
	assert pie[0].parent == "SAL-ORD-2024-00001"

	dn = make_delivery_note("SAL-ORD-2024-00001")
	for item in dn.items[:]:
		if item.item_code == "Ambrosia Pie":
			item.qty = 5
		else:
			dn.remove(item)
	dn.save()
	dn.submit()

	# assert partial allocations
	pie = get_demand(item_code="Ambrosia Pie")
	assert len(pie) == 1

	assert pie[0].total_required_qty == 40
	assert pie[0].net_required_qty == 0
	assert pie[0].allocated_qty == 40
	assert pie[0].warehouse == "Baked Goods - APC"
	assert pie[0].parent == "SAL-ORD-2024-00001"


@pytest.mark.order(5)
def test_allocation_reversal_on_delivery_cancel():
	dn = frappe.get_doc("Delivery Note", "MAT-DN-2024-00001")
	dn.cancel()

	pie = get_demand(item_code="Ambrosia Pie")
	assert len(pie) == 1

	# demand + allocation from stock entry
	assert pie[0].total_required_qty == 40
	assert pie[0].net_required_qty == 5
	assert pie[0].allocated_qty == 35  # 30 from stock entry plus 5 from delivery note
	assert pie[0].warehouse == "Baked Goods - APC"
	assert pie[0].parent == "SAL-ORD-2024-00001"


@pytest.mark.order(13)
def test_allocation_from_purchasing():
	for pr in frappe.get_all(
		"Purchase Receipt", ["name", "'Purchase Receipt' AS doctype"]
	) + frappe.get_all("Purchase Invoice", ["name", "'Purchase Invoice' AS doctype"]):
		pr = frappe.get_doc(pr.doctype, pr.name)
		for row in pr.items:
			if row.handling_unit:  # flag for inventoriable item
				# TODO: this should be improved with greater specificity, but detecting that creating inventory leads to modification of the demand db is OK for now
				d = get_demand(pr.company, item_code=row.item_code)
				assert len(d) > 0
