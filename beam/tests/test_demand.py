# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import random
from pathlib import Path

import frappe
import pytest
from erpnext.selling.doctype.sales_order.sales_order import make_delivery_note
from frappe.utils import add_days, get_site_path, today

from beam.beam.demand.demand import (
	build_demand_allocation_map,
	get_demand,
	get_manufacturing_demand,
	get_sales_demand,
)
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

	sales_demand = get_sales_demand()
	assert sales_demand[0].item_code == "Ambrosia Pie"
	assert sales_demand[1].item_code == "Double Plum Pie"
	assert sales_demand[2].item_code == "Gooseberry Pie"
	assert sales_demand[3].item_code == "Kaduka Key Lime Pie"

	wos = frappe.get_all("Work Order", ["production_item"], order_by="name ASC")

	assert wos[0].get("production_item") == "Ambrosia Pie Filling"
	assert wos[1].get("production_item") == "Double Plum Pie Filling"
	assert wos[2].get("production_item") == "Gooseberry Pie Filling"
	assert wos[3].get("production_item") == "Kaduka Key Lime Pie Filling"
	assert wos[4].get("production_item") == "Pie Crust"
	assert wos[5].get("production_item") == "Ambrosia Pie"
	assert wos[6].get("production_item") == "Double Plum Pie"
	assert wos[7].get("production_item") == "Gooseberry Pie"
	assert wos[8].get("production_item") == "Kaduka Key Lime Pie"

	# [print(f"assert wos[{idx}].get('production_item') == '{m.get('production_item')}'") for idx, m in enumerate(wos)]

	manufacturing_demand = get_manufacturing_demand()
	# [
	# 	print(
	# 		f"assert manufacturing_demand[{idx}].get('parent') == '{m.get('parent')}'" + '\n' +
	# 		f"assert manufacturing_demand[{idx}].get('item_code') == '{m.get('item_code')}'"
	# 	)
	# 	for idx, m in enumerate(manufacturing_demand)
	# ]

	# assert frappe.get_value('Work Order', manufacturing_demand[0].get('parent'), 'production_item') == 'Kaduka Key Lime Pie Filling'
	assert manufacturing_demand[0].get("parent") == "MFG-WO-2024-00001"
	assert manufacturing_demand[0].get("item_code") == "Butter"
	assert manufacturing_demand[1].get("parent") == "MFG-WO-2024-00001"
	assert manufacturing_demand[1].get("item_code") == "Cloudberry"
	assert manufacturing_demand[2].get("parent") == "MFG-WO-2024-00001"
	assert manufacturing_demand[2].get("item_code") == "Cornstarch"
	assert manufacturing_demand[3].get("parent") == "MFG-WO-2024-00001"
	assert manufacturing_demand[3].get("item_code") == "Hairless Rambutan"
	assert manufacturing_demand[4].get("parent") == "MFG-WO-2024-00001"
	assert manufacturing_demand[4].get("item_code") == "Sugar"
	assert manufacturing_demand[5].get("parent") == "MFG-WO-2024-00001"
	assert manufacturing_demand[5].get("item_code") == "Tayberry"
	assert manufacturing_demand[6].get("parent") == "MFG-WO-2024-00001"
	assert manufacturing_demand[6].get("item_code") == "Water"
	assert manufacturing_demand[7].get("parent") == "MFG-WO-2024-00002"
	assert manufacturing_demand[7].get("item_code") == "Butter"
	assert manufacturing_demand[8].get("parent") == "MFG-WO-2024-00002"
	assert manufacturing_demand[8].get("item_code") == "Cocoplum"
	assert manufacturing_demand[9].get("parent") == "MFG-WO-2024-00002"
	assert manufacturing_demand[9].get("item_code") == "Cornstarch"
	assert manufacturing_demand[10].get("parent") == "MFG-WO-2024-00002"
	assert manufacturing_demand[10].get("item_code") == "Damson Plum"
	assert manufacturing_demand[11].get("parent") == "MFG-WO-2024-00002"
	assert manufacturing_demand[11].get("item_code") == "Sugar"
	assert manufacturing_demand[12].get("parent") == "MFG-WO-2024-00002"
	assert manufacturing_demand[12].get("item_code") == "Water"
	assert manufacturing_demand[13].get("parent") == "MFG-WO-2024-00003"
	assert manufacturing_demand[13].get("item_code") == "Butter"
	assert manufacturing_demand[14].get("parent") == "MFG-WO-2024-00003"
	assert manufacturing_demand[14].get("item_code") == "Cornstarch"
	assert manufacturing_demand[15].get("parent") == "MFG-WO-2024-00003"
	assert manufacturing_demand[15].get("item_code") == "Gooseberry"
	assert manufacturing_demand[16].get("parent") == "MFG-WO-2024-00003"
	assert manufacturing_demand[16].get("item_code") == "Sugar"
	assert manufacturing_demand[17].get("parent") == "MFG-WO-2024-00003"
	assert manufacturing_demand[17].get("item_code") == "Water"
	assert manufacturing_demand[18].get("parent") == "MFG-WO-2024-00004"
	assert manufacturing_demand[18].get("item_code") == "Butter"
	assert manufacturing_demand[19].get("parent") == "MFG-WO-2024-00004"
	assert manufacturing_demand[19].get("item_code") == "Cornstarch"
	assert manufacturing_demand[20].get("parent") == "MFG-WO-2024-00004"
	assert manufacturing_demand[20].get("item_code") == "Kaduka Lime"
	assert manufacturing_demand[21].get("parent") == "MFG-WO-2024-00004"
	assert manufacturing_demand[21].get("item_code") == "Limequat"
	assert manufacturing_demand[22].get("parent") == "MFG-WO-2024-00004"
	assert manufacturing_demand[22].get("item_code") == "Sugar"
	assert manufacturing_demand[23].get("parent") == "MFG-WO-2024-00004"
	assert manufacturing_demand[23].get("item_code") == "Water"
	assert manufacturing_demand[24].get("parent") == "MFG-WO-2024-00005"
	assert manufacturing_demand[24].get("item_code") == "Butter"
	assert manufacturing_demand[25].get("parent") == "MFG-WO-2024-00005"
	assert manufacturing_demand[25].get("item_code") == "Flour"
	assert manufacturing_demand[26].get("parent") == "MFG-WO-2024-00005"
	assert manufacturing_demand[26].get("item_code") == "Ice Water"
	assert manufacturing_demand[27].get("parent") == "MFG-WO-2024-00005"
	assert manufacturing_demand[27].get("item_code") == "Parchment Paper"
	assert manufacturing_demand[28].get("parent") == "MFG-WO-2024-00005"
	assert manufacturing_demand[28].get("item_code") == "Pie Tin"
	assert manufacturing_demand[29].get("parent") == "MFG-WO-2024-00005"
	assert manufacturing_demand[29].get("item_code") == "Salt"
	assert manufacturing_demand[30].get("parent") == "MFG-WO-2024-00006"
	assert manufacturing_demand[30].get("item_code") == "Ambrosia Pie Filling"
	assert manufacturing_demand[31].get("parent") == "MFG-WO-2024-00006"
	assert manufacturing_demand[31].get("item_code") == "Pie Box"
	assert manufacturing_demand[32].get("parent") == "MFG-WO-2024-00006"
	assert manufacturing_demand[32].get("item_code") == "Pie Crust"
	assert manufacturing_demand[33].get("parent") == "MFG-WO-2024-00007"
	assert manufacturing_demand[33].get("item_code") == "Double Plum Pie Filling"
	assert manufacturing_demand[34].get("parent") == "MFG-WO-2024-00007"
	assert manufacturing_demand[34].get("item_code") == "Pie Box"
	assert manufacturing_demand[35].get("parent") == "MFG-WO-2024-00007"
	assert manufacturing_demand[35].get("item_code") == "Pie Crust"
	assert manufacturing_demand[36].get("parent") == "MFG-WO-2024-00008"
	assert manufacturing_demand[36].get("item_code") == "Gooseberry Pie Filling"
	assert manufacturing_demand[37].get("parent") == "MFG-WO-2024-00008"
	assert manufacturing_demand[37].get("item_code") == "Pie Box"
	assert manufacturing_demand[38].get("parent") == "MFG-WO-2024-00008"
	assert manufacturing_demand[38].get("item_code") == "Pie Crust"
	assert manufacturing_demand[39].get("parent") == "MFG-WO-2024-00009"
	assert manufacturing_demand[39].get("item_code") == "Kaduka Key Lime Pie Filling"
	assert manufacturing_demand[40].get("parent") == "MFG-WO-2024-00009"
	assert manufacturing_demand[40].get("item_code") == "Pie Box"
	assert manufacturing_demand[41].get("parent") == "MFG-WO-2024-00009"
	assert manufacturing_demand[41].get("item_code") == "Pie Crust"

	build_demand_allocation_map()

	# get demand assert that correct quantities and allocations exist
	water = get_demand(filters={"item_code": "Water"})
	assert len(water) == 4

	assert water[0].parent == "MFG-WO-2024-00001"
	assert water[0].total_required_qty == 10.0
	assert water[0].net_required_qty == 1.0
	assert water[0].allocated_qty == 9.0
	assert water[0].warehouse == "Refrigerator - APC"

	assert water[1].parent == "MFG-WO-2024-00002"
	assert water[1].total_required_qty == 10.0
	assert water[1].net_required_qty == 10.0
	assert water[1].allocated_qty == 0.0
	assert water[1].warehouse == "Kitchen - APC"

	assert water[2].parent == "MFG-WO-2024-00003"
	assert water[2].total_required_qty == 2.5
	assert water[2].net_required_qty == 2.5
	assert water[2].allocated_qty == 0.0
	assert water[2].warehouse == "Kitchen - APC"

	assert water[3].parent == "MFG-WO-2024-00004"
	assert water[3].total_required_qty == 2.5
	assert water[3].net_required_qty == 2.5
	assert water[3].allocated_qty == 0.0
	assert water[3].warehouse == "Kitchen - APC"

	ice_water = get_demand(filters={"item_code": "Ice Water"})
	assert len(ice_water) == 1

	assert ice_water[0].parent == "MFG-WO-2024-00005"
	assert ice_water[0].total_required_qty == 50
	assert ice_water[0].net_required_qty == 39.0
	assert ice_water[0].allocated_qty == 11.0
	assert ice_water[0].warehouse == "Refrigerator - APC"


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
	water = get_demand(filters={"item_code": "Water"})
	assert len(water) == 4

	assert water[0].parent == "MFG-WO-2024-00001"
	assert water[0].total_required_qty == 10.0
	assert water[0].net_required_qty == 0.0
	assert water[0].allocated_qty == 10.0
	assert water[0].warehouse == "Refrigerator - APC"

	assert water[1].parent == "MFG-WO-2024-00002"
	assert water[1].total_required_qty == 10.0
	assert water[1].net_required_qty == 10.0
	assert water[1].allocated_qty == 0.0
	assert water[1].warehouse == "Kitchen - APC"

	assert water[2].parent == "MFG-WO-2024-00003"
	assert water[2].total_required_qty == 2.5
	assert water[2].net_required_qty == 2.5
	assert water[2].allocated_qty == 0.0
	assert water[2].warehouse == "Kitchen - APC"

	assert water[3].parent == "MFG-WO-2024-00004"
	assert water[3].total_required_qty == 2.5
	assert water[3].net_required_qty == 2.5
	assert water[3].allocated_qty == 0.0
	assert water[3].warehouse == "Kitchen - APC"

	# assert partial allocations
	ice_water = get_demand(filters={"item_code": "Ice Water"})
	assert len(ice_water) == 1

	assert ice_water[0].total_required_qty == 50
	assert ice_water[0].net_required_qty == 0
	assert ice_water[0].allocated_qty == 50
	assert ice_water[0].warehouse == "Refrigerator - APC"
	assert ice_water[0].parent == "MFG-WO-2024-00005"


@pytest.mark.order(31)  # run after other tests
def test_demand_removal_on_order_cancel():
	pie = get_demand(filters={"item_code": "Ambrosia Pie"})
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

	pie = get_demand(filters={"item_code": "Ambrosia Pie"})
	assert len(pie) == 2

	so.cancel()
	so.delete()

	pie = get_demand(filters={"item_code": "Ambrosia Pie"})
	assert len(pie) == 1


@pytest.mark.order(32)  # run after other tests
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
	pie = get_demand(filters={"item_code": "Ambrosia Pie"})
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
	pie = get_demand(filters={"item_code": "Ambrosia Pie"})
	assert len(pie) == 1

	assert pie[0].total_required_qty == 35
	assert pie[0].net_required_qty == 0
	assert pie[0].allocated_qty == 35
	assert pie[0].warehouse == "Baked Goods - APC"
	assert pie[0].parent == "SAL-ORD-2024-00001"


@pytest.mark.order(33)  # run after other tests
def test_allocation_reversal_on_delivery_cancel():
	dn = frappe.get_doc("Delivery Note", "MAT-DN-2024-00001")
	dn.cancel()

	pie = get_demand(filters={"item_code": "Ambrosia Pie"})
	assert len(pie) == 1

	# demand + allocation from stock entry
	assert pie[0].total_required_qty == 40
	assert pie[0].net_required_qty == 0
	assert pie[0].allocated_qty == 40
	assert pie[0].warehouse == "Baked Goods - APC"
	assert pie[0].parent == "SAL-ORD-2024-00001"


@pytest.mark.order(13)
def test_allocation_from_purchasing():
	receipts = frappe.get_all(
		"Purchase Receipt", ["name", "'Purchase Receipt' AS doctype"]
	) + frappe.get_all("Purchase Invoice", ["name", "'Purchase Invoice' AS doctype"])

	for pr in receipts:
		doc = frappe.get_doc(pr.doctype, pr.name)
		for item in doc.items:
			if item.handling_unit:  # flag for inventoriable item
				# TODO: this should be improved with greater specificity, but detecting that
				# creating inventory leads to modification of the demand db is OK for now
				d = get_demand(filters={"item_code": item.item_code})
				assert len(d) > 0
