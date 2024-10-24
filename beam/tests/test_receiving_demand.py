# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

# test update with purchase receipt submission
# test update with purchase receipt cancellation
# test demand from unfilled qty on blanket order
# test demand from purchase invoice without PO
#
# For license information, please see license.txt


import frappe
import pytest

from beam.beam.demand.receiving import (
	_get_receiving_demand,
	get_receiving_demand,
	reset_build_receiving_map,
)


@pytest.mark.order(2)
def test_opening_receiving():
	receiving_demand = _get_receiving_demand()
	assert receiving_demand[0].item_code == "Cloudberry"
	assert receiving_demand[1].item_code == "Hairless Rambutan"
	assert receiving_demand[2].item_code == "Tayberry"
	assert receiving_demand[3].item_code == "Cocoplum"
	assert receiving_demand[4].item_code == "Damson Plum"
	assert receiving_demand[5].item_code == "Gooseberry"
	assert receiving_demand[6].item_code == "Kaduka Lime"
	assert receiving_demand[7].item_code == "Limequat"
	assert receiving_demand[8].item_code == "Butter"
	assert receiving_demand[9].item_code == "Cornstarch"
	assert receiving_demand[10].item_code == "Flour"
	assert receiving_demand[11].item_code == "Salt"
	assert receiving_demand[12].item_code == "Sugar"
	assert receiving_demand[13].item_code == "Water"
	assert receiving_demand[14].item_code == "Parchment Paper"
	assert receiving_demand[15].item_code == "Pie Box"
	assert receiving_demand[16].item_code == "Pie Tin"

	reset_build_receiving_map()

	water = get_receiving_demand(filters={"item_code": "Water"})
	assert len(water) == 1

	assert water[0].parent == "PUR-ORD-2024-00002"
	assert water[0].stock_qty == 24.999442
	assert water[0].warehouse == "Kitchen - APC"


@pytest.mark.order(31)
def test_demand_from_purchase_invoice_without_po():

	receiving_demand = get_receiving_demand(filters={"doctype": "Purchase Invoice"})
	assert len(receiving_demand) == 0

	pi = frappe.new_doc("Purchase Invoice")
	pi.supplier = "Freedom Provisions"
	pi.set_posting_time = True
	pi.buying_price_list = "Bakery Buying"
	item = frappe.get_doc("Item", "Butter")
	pi.append(
		"items",
		{
			"item_code": item.item_code,
			"warehouse": "Refrigerator - APC",
			"rejected_warehouse": "Storeroom - APC",
			"received_qty": 0,
			"qty": 10,
			"rate": 10,
		},
	)
	pi.save()
	pi.submit()

	receiving_demand = get_receiving_demand(filters={"doctype": "Purchase Invoice"})
	assert len(receiving_demand) == 1

	pi.cancel()

	receiving_demand = get_receiving_demand(filters={"doctype": "Purchase Invoice"})
	assert len(receiving_demand) == 0
