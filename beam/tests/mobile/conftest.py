# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import re

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


def get_local_url():
	url = frappe.utils.get_url()
	# Only force http for local development
	if re.search(r"(127\.0\.0\.1|localhost|\.localhost)", url):
		url = url.replace("https://", "http://")
	return url


@pytest.fixture(autouse=True)
def setup(page):
	# delete all existing draft Purchase Receipts
	delete_draft_records(["Purchase Receipt", "Stock Entry"])

	page.set_default_timeout(30000)

	base_url = get_local_url()

	page.goto(base_url)
	page.wait_for_load_state("networkidle")

	# visiting the home page redirects to login page
	# page.get_by_role("textbox", name="Email").fill("support@agritheory.dev")
	# page.get_by_role("textbox", name="Password").fill("admin")
	page.locator("#login_email").fill("support@agritheory.dev")
	page.locator("#login_password").fill("admin")
	page.locator(".btn-login").click()
	# page.get_by_role("button", name="Login").click()  # this will redirect to `/beam`
	yield

	# delete all Purchase Receipts created during the test
	receipts = frappe.get_all(
		"Purchase Receipt", filters={"docstatus": ["in", [1, 2]]}, fields=["name", "docstatus"]
	)
	for receipt in receipts:
		receipt_doc = frappe.get_doc("Purchase Receipt", receipt.name)
		if receipt.docstatus == 1:
			receipt_doc.cancel()
		# only delete if the document is in draft state, since cancelled documents are
		# linked to SLEs, which can't be deleted
		elif receipt.docstatus == 0:
			receipt_doc.delete()


def delete_draft_records(doctypes: list[str]):
	for doctype in doctypes:
		records = frappe.get_all(doctype, filters={"docstatus": 0}, pluck="name")
		for record in records:
			frappe.delete_doc(doctype, record, force=True)
