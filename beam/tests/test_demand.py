from pathlib import Path

import frappe
import pytest
from frappe.utils import get_site_path

from beam.beam.demand.demand import build_demand_map, get_demand

# TODO:
# configure rejected warehouse and make sure its under test for demand
# debug allocation issues when
# add filters to Demand Map: manufactured items, purchased items, finished goods
#


@pytest.mark.order(1)
def test_opening_demand():
	# destroy and reset
	demand_db_path = Path(f"{get_site_path()}/demand.db").resolve()
	if demand_db_path.exists():
		demand_db_path.unlink(missing_ok=True)

	build_demand_map()
	# get demand assert that correct quantities and allocations exist
	water = get_demand(company=frappe.defaults.get_defaults().get("company"), item_code="Water")

	assert len(water) == 4

	assert water[0].total_required_qty == 10.0
	assert water[0].net_required_qty == 10.0
	assert water[0].allocated_qty == 0.0
	assert water[0].warehouse == "Kitchen - APC"
	assert water[0].parent == "MFG-WO-2024-00007"

	assert water[1].total_required_qty == 2.5
	assert water[1].net_required_qty == 2.5
	assert water[1].allocated_qty == 0
	assert water[1].warehouse == "Kitchen - APC"
	assert water[1].parent == "MFG-WO-2024-00008"

	assert water[2].total_required_qty == 2.5
	assert water[2].net_required_qty == 2.5
	assert water[2].allocated_qty == 0
	assert water[2].warehouse == "Kitchen - APC"
	assert water[2].parent == "MFG-WO-2024-00009"

	assert water[3].total_required_qty == 10.0
	assert water[3].net_required_qty == 1.0
	assert water[3].allocated_qty == 9.0
	assert water[3].warehouse == "Refrigerator - APC"
	assert water[3].parent == "MFG-WO-2024-00006"

	ice_water = get_demand(
		company=frappe.defaults.get_defaults().get("company"), item_code="Ice Water"
	)

	assert len(ice_water) == 1

	assert ice_water[0].total_required_qty == 50
	assert ice_water[0].net_required_qty == 39
	assert ice_water[0].allocated_qty == 11
	assert ice_water[0].warehouse == "Refrigerator - APC"
	assert ice_water[0].parent == "MFG-WO-2024-00005"


@pytest.mark.order(2)
def test_insufficient_total_demand_scenario():
	# test multiple partial allocations
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
	water = get_demand(company=se.company, item_code="Water")

	assert len(water) == 5

	assert water[0].total_required_qty == 2.5
	assert water[0].net_required_qty == 2.5
	assert water[0].allocated_qty == 0
	assert water[0].warehouse == "Kitchen - APC"
	assert water[0].parent == "MFG-WO-2024-00009"

	assert water[1].total_required_qty == 10.0
	assert water[1].net_required_qty == 0.0
	assert water[1].allocated_qty == 9.0
	assert water[1].warehouse == "Refrigerator - APC"
	assert water[1].parent == "MFG-WO-2024-00006"

	assert water[2].total_required_qty == 10.0
	assert water[2].net_required_qty == 0.0
	assert water[2].allocated_qty == 1.0
	assert water[2].warehouse == "Refrigerator - APC"
	assert water[2].parent == "MFG-WO-2024-00006"

	assert water[3].total_required_qty == 10.0
	assert water[3].net_required_qty == 0.0
	assert water[3].allocated_qty == 10.0
	assert water[3].warehouse == "Refrigerator - APC"
	assert water[3].parent == "MFG-WO-2024-00007"

	assert water[4].total_required_qty == 2.5
	assert water[4].net_required_qty == 0.0
	assert water[4].allocated_qty == 2.5
	assert water[4].warehouse == "Refrigerator - APC"
	assert water[4].parent == "MFG-WO-2024-00008"

	# assert partial allocations
	ice_water = get_demand(company=se.company, item_code="Ice Water")

	assert len(ice_water) == 2

	assert ice_water[0].total_required_qty == 50
	assert ice_water[0].net_required_qty == 0.0
	assert ice_water[0].allocated_qty == 11
	assert ice_water[0].warehouse == "Refrigerator - APC"
	assert ice_water[0].parent == "MFG-WO-2024-00005"

	assert ice_water[1].total_required_qty == 50
	assert ice_water[1].net_required_qty == 0.0
	assert ice_water[1].allocated_qty == 39
	assert ice_water[1].warehouse == "Refrigerator - APC"
	assert ice_water[1].parent == "MFG-WO-2024-00005"

	# assert make-up allocation and not over-allocation


@pytest.mark.order(13)
def test_allocation_from_purchasing():
	for pr in frappe.get_all(
		"Purchase Receipt", ["name", "'Purchase Receipt' AS doctype"]
	) + frappe.get_all("Purchase Invoice", ["name", "'Purchase Invoice' AS doctype"]):
		pr = frappe.get_doc(pr.doctype, pr.name)
		for row in pr.items:
			if row.handling_unit:  # flag for inventoriable item
				d = get_demand(pr.company, item_code=row.item_code)
				assert len(d) > 0
				total_demand = sum(i.allocated_qty for i in d) or 0
				print(row.item_code, total_demand, row.stock_qty)
				[print(l) for l in d]
