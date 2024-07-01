import base64
import uuid
from io import BytesIO, StringIO

import barcode
import frappe
import zebra_zpl


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
	barcode.Code128(barcode_text, writer=barcode.writer.ImageWriter()).write(
		temp,
		options={"module_width": 0.4, "module_height": 10, "font_size": 0, "compress": True},
	)
	encoded = base64.b64encode(temp.getvalue()).decode("ascii")
	return f'<img src="data:image/png;base64,{encoded}"/>'


@frappe.whitelist()
@frappe.read_only()
def formatted_zpl_barcode(barcode_text: str) -> str:
	bc = zebra_zpl.Barcode(
		barcode_text,
		type="C",
		human_readable="Y",
		width=4,
		height=260,
		ratio=1,
		justification="C",
		position=(20, 40),
	)
	b = bc.to_zpl()
	return b


@frappe.whitelist()
@frappe.read_only()
def formatted_zpl_label(
	width: str, length: str, dpi: str = 203, print_speed: int = 2, copies: int = 1
) -> str:
	l = frappe._dict({})
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
def formatted_zpl_text(text: str, width: None) -> str:
	tf = zebra_zpl.Text(
		text, font_type=0, font_size=28, position=(0, 25), width=width, y=25, justification="C"
	)
	t = tf.to_zpl()
	return t


@frappe.whitelist()
@frappe.read_only()
def zebra_zpl_label(*args, **kwargs):
	l = ZPLLabelStringOutput()
	for key, value in kwargs.items():
		l[key] = value
	return l


@frappe.whitelist()
@frappe.read_only()
def zebra_zpl_barcode(*args, **kwargs):
	return zebra_zpl.Barcode(*args, **kwargs)


@frappe.whitelist()
@frappe.read_only()
def zebra_zpl_text(*args, **kwargs):
	return zebra_zpl.Text(*args, **kwargs)


@frappe.whitelist()
@frappe.read_only()
def add_to_label(label, *args, **kwargs):
	label.add(*args, **kwargs)


class ZPLLabelStringOutput(zebra_zpl.Label):
	def __getitem__(self, key):
		return getattr(self, key)

	def __setitem__(self, key, value):
		setattr(self, key, value)

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
