import base64
import uuid
from io import BytesIO

import barcode
import frappe


@frappe.whitelist()
def create_beam_barcode(doc, method=None):
	if doc.doctype == "Item" and doc.is_stock_item == 0:
		return
	if (
		doc.get("item_group")
		and doc.doctype == "Item"
		and frappe.db.exists("Item Group", "Products")
		and doc.item_group
		in frappe.get_all("Item Group", {"name": ("descendants of", "Products")}, pluck="name")
	):
		# TODO: refactor this to be configurable to "Products" or "sold" items that do not require handling units
		return
	if any([b for b in doc.barcodes if b.barcode_type == "Code128"]):
		return
	# move all other rows back
	for row_index, b in enumerate(doc.barcodes, start=1):
		b.idx = row_index + 1
	doc.append(
		"barcodes",
		{"barcode": str(uuid.uuid4().int >> 64), "barcode_type": "Code128", "idx": 1},
	)
	return doc


@frappe.whitelist()
@frappe.read_only()
def barcode128(barcode_text: str) -> str:
	if not barcode_text:
		return ""
	temp = BytesIO()
	barcode.Code128(barcode_text, writer=barcode.writer.ImageWriter()).write(
		temp,
		options={"module_width": 0.4, "module_height": 10, "font_size": 0, "compress": True},
	)
	encoded = base64.b64encode(temp.getvalue()).decode("ascii")
	return f'<img src="data:image/png;base64,{encoded}"/>'
