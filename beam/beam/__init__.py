import frappe
from frappe.utils.jinja import get_jinja_hooks
from frappe.utils.safe_exec import get_safe_globals
from jinja2 import DebugUndefined, Environment

import imgkit
import base64
from io import BytesIO

def image_preview(print_format, doc):
	print_format = frappe.get_doc('Print Format', print_format)
	output = ""
	e = Environment(undefined=DebugUndefined)
	e.globals.update(get_safe_globals())
	e.globals.update(get_jinja_hooks()[0])
	template = e.from_string(print_format.html)
	output = template.render(doc=doc)
	image = BytesIO(imgkit.from_string(f"<html>{output}</html>", False))
	return base64.b64encode(image.getvalue()).decode("ascii")

