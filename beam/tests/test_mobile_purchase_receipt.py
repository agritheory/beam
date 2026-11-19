# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest
from erpnext.buying.doctype.purchase_order.purchase_order import make_purchase_receipt

from beam.beam.mobile_purchase_receipt import purchase_receipt_from_route_id

COMPANY = "Ambrosia Pie Company"
SUPPLIER = "Freedom Provisions"
WAREHOUSE = "Receiving - APC"
ORDER_ITEMS = ["Butter", "Sugar", "Salt"]


def make_purchase_order() -> str:
	po = frappe.new_doc("Purchase Order")
	po.supplier = SUPPLIER
	po.company = COMPANY
	po.schedule_date = frappe.utils.today()
	for item_code in ORDER_ITEMS:
		po.append("items", {"item_code": item_code, "qty": 5, "rate": 1, "warehouse": WAREHOUSE})
	po.insert()
	po.submit()
	return po.name


def make_draft_receipt(
	purchase_order: str, item_codes: list[str], taxes: list[dict] | None = None
):
	"""Draft receipt with only some order lines, as mobile saves a partial receipt."""
	pr = make_purchase_receipt(purchase_order)
	pr.items = [row for row in pr.items if row.item_code in item_codes]
	if taxes is not None:
		pr.taxes_and_charges = None
		pr.set("taxes", taxes)
	pr.insert()
	return pr


@pytest.mark.order(94)
def test_reopening_draft_restores_pending_order_lines():
	purchase_order = make_purchase_order()
	draft = make_draft_receipt(purchase_order, ["Sugar"])

	doc = purchase_receipt_from_route_id(purchase_order)

	assert doc.name == draft.name
	assert [row.item_code for row in doc.items] == ORDER_ITEMS
	assert [row.idx for row in doc.items] == [1, 2, 3]
	received = {row.item_code: row.received_qty for row in doc.items}
	assert received["Butter"] == 0
	assert received["Salt"] == 0
	assert received["Sugar"] == 5


@pytest.mark.order(95)
def test_reopening_draft_skips_lines_in_another_draft():
	purchase_order = make_purchase_order()
	make_draft_receipt(purchase_order, ["Butter"])
	draft = make_draft_receipt(purchase_order, ["Sugar"])

	doc = purchase_receipt_from_route_id(draft.name)

	assert [row.item_code for row in doc.items] == ["Sugar", "Salt"]


@pytest.mark.order(96)
def test_reopening_draft_keeps_receipt_taxes():
	purchase_order = make_purchase_order()
	account = frappe.db.get_value(
		"Account", {"company": COMPANY, "account_type": "Tax", "is_group": 0}
	)
	tax = {"charge_type": "On Net Total", "account_head": account, "description": "VAT", "rate": 17}
	draft = make_draft_receipt(purchase_order, ["Sugar"], taxes=[tax])

	doc = purchase_receipt_from_route_id(draft.name)

	assert len(doc.items) == len(ORDER_ITEMS)
	assert [(row.account_head, row.rate) for row in doc.taxes] == [(account, 17)]
