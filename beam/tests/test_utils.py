# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

from contextlib import contextmanager
import frappe


@contextmanager
def use_current_db_transaction():
	"""
	Context manager to refresh the database transaction scope.

	This is needed when testing with Playwright because the browser actions
	(like clicking SAVE or RECEIVE) commit data to the database, but the pytest
	context maintains its own transaction scope and can't see the committed data
	until the transaction is refreshed.

	"""
	frappe.db.rollback()
	frappe.db.begin()
	yield
