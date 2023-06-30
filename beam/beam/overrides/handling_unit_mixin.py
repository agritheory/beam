import frappe
from erpnext.accounts.utils import get_fiscal_year
from erpnext.stock.doctype.bin.bin import update_qty as update_bin_qty
from erpnext.stock.stock_ledger import *
from erpnext.stock.stock_ledger import (
	get_args_for_future_sle,
	make_entry,
	repost_current_voucher,
	set_as_cancel,
	validate_cancellation,
	validate_serial_no,
)
from erpnext.stock.utils import get_incoming_outgoing_rate_for_cancel, get_or_make_bin
from frappe import _
from frappe.utils.data import cstr, flt


class HandlingUnitMixin:
	def validate(self):
		self = split_items_according_to_handling_unit_qty(self)

	def before_submit(self):
		self.assign_handling_units()

	def on_cancel(self):
		pass

	def assign_handling_units(self):
		for row in self.items:
			if frappe.get_value("Item", row.item_code, "is_stock_item"):
				handling_unit = frappe.new_doc("Handling Unit")
				handling_unit.save()
				row.handling_unit = handling_unit.name


def assign_handling_unit(self):
	handling_unit = frappe.new_doc("Handling Unit")
	handling_unit.save()
	self.handling_unit = handling_unit.name


def patched_make_sl_entries(sl_entries, allow_negative_stock=False, via_landed_cost_voucher=False):
	"""Create SL entries from SL entry dicts
	args:
	- allow_negative_stock: disable negative stock validations if true
	- via_landed_cost_voucher: landed cost voucher cancels and reposts
	entries of purchase document. This flag is used to identify if
	cancellation and repost is happening via landed cost voucher, in
	such cases certain validations need to be ignored (like negative stock)
	"""
	from erpnext.controllers.stock_controller import future_sle_exists

	if not sl_entries:
		return
	cancel = sl_entries[0].get("is_cancelled")
	if cancel:
		validate_cancellation(sl_entries)
		set_as_cancel(sl_entries[0].get("voucher_type"), sl_entries[0].get("voucher_no"))

	args = get_args_for_future_sle(sl_entries[0])
	future_sle_exists(args, sl_entries)

	for sle in sl_entries:
		if sle.serial_no and not via_landed_cost_voucher:
			validate_serial_no(sle)

		if cancel:
			sle["actual_qty"] = -flt(sle.get("actual_qty"))

			if sle["actual_qty"] < 0 and not sle.get("outgoing_rate"):
				sle["outgoing_rate"] = get_incoming_outgoing_rate_for_cancel(
					sle.item_code, sle.voucher_type, sle.voucher_no, sle.voucher_detail_no
				)
				sle["incoming_rate"] = 0.0

			if sle["actual_qty"] > 0 and not sle.get("incoming_rate"):
				sle["incoming_rate"] = get_incoming_outgoing_rate_for_cancel(
					sle.item_code, sle.voucher_type, sle.voucher_no, sle.voucher_detail_no
				)
				sle["outgoing_rate"] = 0.0

		if sle.get("actual_qty") or sle.get("voucher_type") == "Stock Reconciliation":
			sle_doc = make_entry(sle, allow_negative_stock, via_landed_cost_voucher)

		args = sle_doc.as_dict()

		if sle.get("handling_unit"):
			args["handling_unit"] = sle["handling_unit"]

		if sle.get("voucher_type") == "Stock Reconciliation":
			# preserve previous_qty_after_transaction for qty reposting
			args.previous_qty_after_transaction = sle.get("previous_qty_after_transaction")

		is_stock_item = frappe.get_cached_value("Item", args.get("item_code"), "is_stock_item")

		if is_stock_item:
			bin_name = get_or_make_bin(args.get("item_code"), args.get("warehouse"))
			repost_current_voucher(args, allow_negative_stock, via_landed_cost_voucher)
			update_bin_qty(bin_name, args)
		else:
			frappe.msgprint(
				_("Item {0} ignored since it is not a stock item").format(args.get("item_code"))
			)


def patched_get_sl_entries(self, d, args):
	sl_dict = frappe._dict(
		{
			"item_code": d.get("item_code", None),
			"warehouse": d.get("warehouse", None),
			"posting_date": self.posting_date,
			"posting_time": self.posting_time,
			"fiscal_year": get_fiscal_year(self.posting_date, company=self.company)[0],
			"voucher_type": self.doctype,
			"voucher_no": self.name,
			"voucher_detail_no": d.name,
			"actual_qty": (self.docstatus == 1 and 1 or -1) * flt(d.get("stock_qty")),
			"stock_uom": frappe.db.get_value(
				"Item", args.get("item_code") or d.get("item_code"), "stock_uom"
			),
			"incoming_rate": 0,
			"company": self.company,
			"batch_no": cstr(d.get("batch_no")).strip(),
			"serial_no": d.get("serial_no"),
			"project": d.get("project") or self.get("project"),
			"is_cancelled": 1 if self.docstatus == 2 else 0,
			"handling_unit": d.get("handling_unit") or "",  # this is the patch
		}
	)
	sl_dict.update(args)
	return sl_dict


def split_items_according_to_handling_unit_qty(self):
	new_items = []
	index = 0
	for row in self.get("items"):
		if row.handling_unit:
			index += 1
			new_items.append(row)
			continue
		# get conversion ratio + handling unit from item
		handling_unit = frappe.get_value(
			"UOM Conversion Detail",
			{"parent": row.item_code, "handling_unit": 1},
			["uom", "conversion_factor"],
			as_dict=True,
		)
		if not handling_unit or handling_unit.uom == row.uom:
			index += 1
			new_items.append(row)
			continue

		handling_unit_rows, remainder = divmod(
			(row.get("stock_qty") or row.get("transfer_qty") or row.get("required_qty") or 0),
			handling_unit.conversion_factor,
		)

		for new_qty in range(0, int(handling_unit_rows)):
			index += 1
			new_row = frappe.copy_doc(row)
			new_row.idx = index
			new_row.name = ""
			new_row.uom = handling_unit.uom
			new_row.qty = 1
			if row.get("rate"):
				new_row.rate = row.rate * handling_unit.conversion_factor
				new_row.base_amount = new_row.base_net_amount = new_row.amount = new_row.rate * new_row.qty
			if row.get("transfer_qty"):
				new_row.transfer_qty = handling_unit.conversion_factor
				new_row.conversion_factor = handling_unit.conversion_factor
			if row.get("required_qty"):
				new_row.required_qty = handling_unit.conversion_factor
				new_row.conversion_factor = handling_unit.conversion_factor
			if row.get("stock_qty"):
				new_row.stock_qty = handling_unit.conversion_factor
				new_row.conversion_factor = handling_unit.conversion_factor
			if row.get("received_qty"):
				new_row.received_qty = handling_unit.conversion_factor
			if row.get("received_stock_qty"):
				new_row.received_stock_qty = handling_unit.conversion_factor
			new_items.append(new_row)

		if remainder:
			new_row = frappe.copy_doc(row)
			index += 1
			new_row.name = ""
			new_row.idx = index
			if frappe.get_value("UOM", handling_unit.uom, "must_be_whole_number"):
				new_row.uom = row.stock_uom
				new_row.qty = remainder
			else:
				new_row.uom = handling_unit.uom
				new_row.qty = remainder / handling_unit.conversion_factor
			if row.get("rate"):
				new_row.rate = row.rate * handling_unit.conversion_factor
				new_row.base_amount = new_row.base_net_amount = new_row.amount = new_row.rate * new_row.qty
			if row.get("required_qty"):
				new_row.required_qty = remainder / handling_unit.conversion_factor
			if row.get("stock_qty"):
				new_row.stock_qty = remainder
				new_row.conversion_factor = handling_unit.conversion_factor
			if row.get("transfer_qty"):
				new_row.transfer_qty = remainder
				new_row.conversion_factor = handling_unit.conversion_factor
			if row.get("received_qty"):
				new_row.received_qty = remainder
			if row.get("received_stock_qty"):
				new_row.received_stock_qty = remainder
			new_items.append(new_row)

	self.items = new_items
	return self
