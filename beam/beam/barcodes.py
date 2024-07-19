import base64
import uuid
from io import BytesIO

import frappe
from barcode import Code128
from barcode.writer import ImageWriter
from zebra_zpl import Barcode, Label, Printable, Text


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
		{"barcode": f"{str(uuid.uuid4().int >> 64):020}", "barcode_type": "Code128", "idx": 1},
	)
	return doc


@frappe.whitelist()
@frappe.read_only()
def barcode128(barcode_text: str) -> str:
	if not barcode_text:
		return ""
	temp = BytesIO()
	instance = Code128(barcode_text, writer=ImageWriter())
	instance.write(
		temp,
		options={"module_width": 0.4, "module_height": 10, "font_size": 0, "compress": True},
	)
	encoded = base64.b64encode(temp.getvalue()).decode("ascii")
	return f'<img src="data:image/png;base64,{encoded}"/>'


@frappe.whitelist()
@frappe.read_only()
def formatted_zpl_barcode(barcode_text: str) -> str:
	bc = Barcode(
		barcode_text,
		type="C",
		human_readable="Y",
		width=4,
		height=260,
		ratio=1,
		justification="C",
		position=(20, 40),
	)
	return bc.to_zpl()


@frappe.whitelist()
@frappe.read_only()
def formatted_zpl_label(
	width: int, length: int, dpi: int = 203, print_speed: int = 2, copies: int = 1
) -> frappe._dict:
	l = frappe._dict()
	# ^XA Start format
	# ^LL<label height in dots>,<space between labels in dots>
	# ^LH<label home - x,y coordinates of top left label>
	# ^LS<shift the label to the left(or right)>
	# ^PW<label width in dots>
	# Print Rate(speed) (^PR command)
	l.start = f"^XA^LL{length}^LH0,0^LS10^PW{width}^PR{print_speed}"
	# Specify how many copies to print
	# End format
	l.end = f"^PQ{copies}^XZ\n"
	return l


@frappe.whitelist()
@frappe.read_only()
def formatted_zpl_text(text: str, width: int | None = None) -> str:
	tf = Text(text, font_type=0, font_size=28, position=(0, 25), width=width, y=25, justification="C")
	return tf.to_zpl()


@frappe.whitelist()
@frappe.read_only()
def zebra_zpl_label(*args, **kwargs):
	return ZPLLabelStringOutput(*args, **kwargs)


@frappe.whitelist()
@frappe.read_only()
def zebra_zpl_barcode(data: str, **kwargs):
	return Barcode(data, **kwargs)


@frappe.whitelist()
@frappe.read_only()
def zebra_zpl_text(data: str, **kwargs):
	return Text(data, **kwargs)


@frappe.whitelist()
@frappe.read_only()
def add_to_label(label: Label, element: Printable):
	label.add(element)


class ZPLLabelStringOutput(Label):
	def __init__(
		self, width: int = 100, length: int = 100, dpi: int = 203, print_speed: int = 2, copies: int = 1
	):
		super().__init__(width, length, dpi, print_speed, copies)

	def dump_contents(self, io=None):
		s = ""
		s += f"^XA^LL{self.length}^LH0,0^LS10^PW{self.width}^PR{self.print_speed}"
		for e in self.elements:
			s += e.to_zpl()

		s += f"^PQ{self.copies}^XZ\n"
		return s


"""
{% set label = namespace(zebra_zpl_label(width=4*203, length=6*203, dpi=203)) %}

{{ zpl_text(hu.item_code + " " + hu.warehouse) }}
{{ zpl_text(hu.posting_date + " " + hu.posting_time) }}

{% label.add(zebra_zpl_barcode(hu.handling_unit, width=4, height=260, position=(20, 40), justification="C", ratio=1, human_readable='Y') -%}
{{ label.dump_contents() }}

"""
