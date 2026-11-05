# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

"""Document access for BEAM mobile when desk Stock roles are not assigned."""

from __future__ import annotations

from contextlib import contextmanager

import frappe
from frappe import _
from frappe.permissions import add_permission, update_permission_property

QUALITY_INSPECTION_DOCTYPE = "Quality Inspection"

MOBILE_QUALITY_INSPECTION_ROLES = (
	"BEAM Mobile User",
	"Stock User",
	"Purchase User",
	"Manufacturing User",
)


def user_has_beam_mobile_role() -> bool:
	return "BEAM Mobile User" in frappe.get_roles()


def ensure_document_access(doctype: str, name: str, ptype: str = "read") -> None:
	if frappe.has_permission(doctype, ptype, doc=name):
		return
	if not user_has_beam_mobile_role():
		frappe.has_permission(doctype, ptype, doc=name, throw=True)
	if not frappe.db.exists(doctype, name):
		frappe.throw(_("{0} {1} not found").format(doctype, name))


def ensure_role_quality_inspection_permissions(role: str) -> None:
	if not frappe.db.exists("Role", role):
		return
	if not frappe.db.get_value(
		"Custom DocPerm", {"parent": QUALITY_INSPECTION_DOCTYPE, "role": role, "permlevel": 0}
	):
		add_permission(QUALITY_INSPECTION_DOCTYPE, role, 0)
	for ptype in ("read", "write", "create", "submit"):
		update_permission_property(QUALITY_INSPECTION_DOCTYPE, role, 0, ptype, 1)


def ensure_beam_quality_inspection_permissions() -> None:
	for role in MOBILE_QUALITY_INSPECTION_ROLES:
		ensure_role_quality_inspection_permissions(role)


@contextmanager
def mobile_quality_inspection_write():
	"""Allow draft/submit QI from BEAM when desk only granted select on Quality Inspection."""
	if not user_has_beam_mobile_role():
		yield
		return
	previous = bool(getattr(frappe.flags, "ignore_permissions", False))
	frappe.flags.ignore_permissions = True
	try:
		yield
	finally:
		frappe.flags.ignore_permissions = previous
