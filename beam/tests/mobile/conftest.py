# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import frappe
import pytest


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
	# emulate an Android barcode scanner
	return {
		**browser_context_args,
		"viewport": {
			"width": 400,
			"height": 900,
		},
	}


@pytest.fixture(autouse=True)
def setup(page):
	delete_draft_records(["Purchase Receipt", "Stock Entry"])

	page.set_default_timeout(30000)
	page.goto("http://127.0.0.1:8000")
	page.set_default_timeout(5000)

	page.get_by_role("textbox", name="Email").fill("support@agritheory.dev")
	page.get_by_role("textbox", name="Password").fill("admin")
	page.get_by_role("button", name="Login").click()
	yield

	receipts = frappe.get_all(
		"Purchase Receipt", filters={"docstatus": ["in", [1, 2]]}, fields=["name", "docstatus"]
	)
	for receipt in receipts:
		receipt_doc = frappe.get_doc("Purchase Receipt", receipt.name)
		if receipt.docstatus == 1:
			receipt_doc.cancel()
		elif receipt.docstatus == 0:
			receipt_doc.delete()


def delete_draft_records(doctypes: list[str]):
	for doctype in doctypes:
		records = frappe.get_all(doctype, filters={"docstatus": 0}, pluck="name")
		for record in records:
			frappe.delete_doc(doctype, record, force=True)
