# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

from __future__ import annotations

import copy

import frappe
from frappe.utils import flt

from beam.beam.demand.demand import build_demand_allocation_map
from beam.beam.demand.receiving import reset_build_receiving_map
from beam.tests.manufacturing_test_utils import submit_material_transfer_for_manufacture
from beam.tests.setup import create_pie_crust_pick_demo, seed_settings

PIE_FINISHED = ("Gooseberry Pie", "Kaduka Key Lime Pie")
ASSEMBLE_OP = "Assemble Pie Op"
BAKE_OP = "Bake Op"
COOL_OP = "Cool Pie Op"
BOX_OP = "Box Pie Op"

fixture_snapshot: dict | None = None


def rebuild_demand_databases():
	build_demand_allocation_map()
	reset_build_receiving_map()


def find_pp_work_order(production_item: str) -> str | None:
	return frappe.db.get_value(
		"Work Order",
		{
			"production_item": production_item,
			"qty": 10,
			"docstatus": 1,
			"production_plan": ("is", "set"),
		},
		"name",
		order_by="creation asc",
	)


def job_card_name(work_order: str, operation: str) -> str | None:
	return frappe.db.get_value("Job Card", {"work_order": work_order, "operation": operation}, "name")


def snapshot_job_card(name: str) -> dict:
	jc = frappe.get_doc("Job Card", name)
	return {
		"name": name,
		"docstatus": jc.docstatus,
		"status": jc.status,
		"total_completed_qty": jc.total_completed_qty,
		"time_logs": [copy.deepcopy(row.as_dict()) for row in jc.time_logs],
	}


def restore_job_card(snapshot: dict) -> None:
	jc = frappe.get_doc("Job Card", snapshot["name"])
	if jc.docstatus == 1:
		try:
			jc.cancel()
		except frappe.ValidationError:
			pass
	jc.reload()
	jc.time_logs = []
	for row in snapshot["time_logs"]:
		jc.append("time_logs", row)
	jc.total_completed_qty = snapshot["total_completed_qty"]
	jc.status = snapshot["status"]
	jc.docstatus = 0
	jc.flags.ignore_permissions = True
	jc.save()
	if snapshot["docstatus"] == 1:
		jc.reload()
		jc.submit()


def clear_job_card_to_open(jc_name: str) -> None:
	jc = frappe.get_doc("Job Card", jc_name)
	if jc.docstatus == 1:
		return
	jc.time_logs = []
	jc.total_completed_qty = 0
	jc.status = "Open"
	jc.flags.ignore_permissions = True
	jc.save()


def submit_job_card_complete(jc_name: str) -> None:
	from frappe.utils import now_datetime

	jc = frappe.get_doc("Job Card", jc_name)
	if not jc.time_logs:
		now = now_datetime()
		jc.append(
			"time_logs",
			{"from_time": now, "to_time": now, "time_in_mins": 1, "completed_qty": flt(jc.for_quantity)},
		)
	jc.total_completed_qty = flt(jc.for_quantity)
	jc.flags.ignore_permissions = True
	if jc.docstatus == 0:
		jc.submit()
	else:
		jc.save()


def receipt_work_order_materials(work_order: str, rates: dict[str, float]) -> None:
	wo = frappe.get_doc("Work Order", work_order)
	se = frappe.new_doc("Stock Entry")
	se.stock_entry_type = se.purpose = "Material Receipt"
	for row in wo.required_items:
		rate = rates.get(row.item_code, 1.0)
		warehouse = row.source_warehouse or row.warehouse
		if not warehouse:
			continue
		se.append(
			"items",
			{
				"item_code": row.item_code,
				"qty": flt(row.required_qty),
				"uom": row.uom,
				"stock_uom": row.stock_uom,
				"t_warehouse": warehouse,
				"basic_rate": rate,
				"expense_account": "5119 - Stock Adjustment - APC",
			},
		)
	if not se.items:
		return
	se.save()
	se.submit()


def prepare_workstation_portal_story() -> dict:
	global fixture_snapshot
	settings = seed_settings()
	create_workstation_fields_if_needed()

	work_orders = {}
	snapshots = []

	for item in PIE_FINISHED:
		wo_name = find_pp_work_order(item)
		assert wo_name, f"Expected production-plan Work Order for {item}"
		work_orders[item] = wo_name

		for op in (ASSEMBLE_OP, BAKE_OP, COOL_OP, BOX_OP):
			jc = job_card_name(wo_name, op)
			assert jc, f"Missing {op} job card on {wo_name}"
			snapshots.append(snapshot_job_card(jc))

		assemble = job_card_name(wo_name, ASSEMBLE_OP)
		submit_job_card_complete(assemble)

		for op in (BAKE_OP, COOL_OP, BOX_OP):
			clear_job_card_to_open(job_card_name(wo_name, op))

	receipt_rates = {
		"Pie Crust": 2.0,
		"Gooseberry Pie Filling": 1.0,
		"Kaduka Key Lime Pie Filling": 1.0,
		"Pie Box": 0.5,
	}
	gooseberry_wo = work_orders["Gooseberry Pie"]
	receipt_work_order_materials(gooseberry_wo, receipt_rates)
	transfer_name = submit_material_transfer_for_manufacture(gooseberry_wo, 10)

	create_pie_crust_pick_demo(settings)

	frappe.db.commit()

	fixture_snapshot = {
		"snapshots": snapshots,
		"work_orders": work_orders,
		"gooseberry_transfer": transfer_name,
	}
	return fixture_snapshot


def create_workstation_fields_if_needed() -> None:
	if frappe.get_meta("Workstation").has_field("require_user_scan"):
		return
	from beam.patches.v15.workstation_tablet_fields import execute

	execute()
	if frappe.db.exists("Workstation", "Oven Station"):
		frappe.db.set_value(
			"Workstation",
			"Oven Station",
			{"require_user_scan": 1, "user_scan_idle_minutes": 15},
		)


def teardown_workstation_portal_story() -> None:
	global fixture_snapshot
	if not fixture_snapshot:
		return

	for wo in fixture_snapshot["work_orders"].values():
		for entry in frappe.get_all(
			"Stock Entry",
			filters={"work_order": wo, "docstatus": 1},
			pluck="name",
		):
			try:
				frappe.get_doc("Stock Entry", entry).cancel()
			except frappe.ValidationError:
				pass

	for snap in fixture_snapshot["snapshots"]:
		restore_job_card(snap)

	frappe.db.commit()
	rebuild_demand_databases()
	fixture_snapshot = None
