import base64
import json
import os
from pathlib import Path

import frappe
import requests
from frappe.utils.jinja import get_jinja_hooks
from frappe.utils.safe_exec import get_safe_globals
from jinja2 import DebugUndefined, Environment
from PyPDF2 import PdfFileWriter

try:
	import cups
except Exception as e:
	frappe.log_error(e, "CUPS is not installed on this server")


@frappe.whitelist()
def print_by_server(
	doctype,
	name,
	printer_setting,
	print_format=None,
	doc=None,
	no_letterhead=0,
	file_path=None,
):
	print_settings = frappe.get_doc("Network Printer Settings", printer_setting)
	if isinstance(doc, str):
		doc = frappe._dict(json.loads(doc))
	if not print_format:
		print_format = frappe.get_meta(doctype).get("default_print_format")
	print_format = frappe.get_doc("Print Format", print_format)
	try:
		cups.setServer(print_settings.server_ip)
		cups.setPort(print_settings.port)
		conn = cups.Connection()
		if print_format.raw_printing == 1:
			output = ""
			# using a custom jinja environment so we don't have to use frappe's formatting
			methods, filters = get_jinja_hooks()
			e = Environment(undefined=DebugUndefined)
			e.globals.update(get_safe_globals())
			e.filters.update(
				{
					"json": frappe.as_json,
					"len": len,
					"int": frappe.utils.data.cint,
					"str": frappe.utils.data.cstr,
					"flt": frappe.utils.data.flt,
				}
			)
			if methods:
				e.globals.update(methods)
			template = e.from_string(print_format.raw_commands)
			output = template.render(doc=doc)
			if not file_path:
				# use this path for testing, it will be available from the public server with the file name
				# file_path = f"{get_bench_path()}/sites{get_files_path()[1:]}/{name}{random_string(10).upper()}.txt"
				# use this technique for production
				file_path = os.path.join("/", "tmp", f"frappe-zpl-{frappe.generate_hash()}.txt")
			Path(file_path).write_text(output)
		else:
			output = PdfFileWriter()
			output = frappe.get_print(
				doctype,
				name,
				print_format.name,
				doc=doc,
				no_letterhead=no_letterhead,
				as_pdf=True,
				output=output,
			)
			if not file_path:
				file_path = os.path.join("/", "tmp", f"frappe-pdf-{frappe.generate_hash()}.pdf")
				output.write(open(file_path, "wb"))
		conn.printFile(print_settings.printer_name, file_path, name, {})
		frappe.msgprint(
			f"{name } printing on {print_settings.printer_name}", alert=True, indicator="green"
		)
	except OSError as e:
		if (
			"ContentNotFoundError" in e.message
			or "ContentOperationNotPermittedError" in e.message
			or "UnknownContentError" in e.message
			or "RemoteHostClosedError" in e.message
		):
			frappe.throw(frappe._("PDF generation failed"))
	except cups.IPPError:
		frappe.throw(frappe._("Printing failed"))


@frappe.whitelist()
def print_handling_units(
	doctype=None, name=None, printer_setting=None, print_format=None, doc=None
):
	if isinstance(doc, str):
		doc = frappe._dict(json.loads(doc))

	for row in doc.get("items"):
		if not row.get("handling_unit"):
			continue
		# only print output / scrap items from Stock Entry
		if doctype == "Stock Entry" and not row.get("t_warehouse"):
			continue
		# if one of the transfer types, use the 'to_handling_unit' field instead
		if doctype == "Stock Entry" and doc.get("purpose") in (
			"Material Transfer",
			"Send to Subcontractor",
			"Material Transfer for Manufacture",
		):
			handling_unit = frappe.get_doc("Handling Unit", row.get("to_handling_unit"))
		else:
			handling_unit = frappe.get_doc("Handling Unit", row.get("handling_unit"))
		print_by_server(
			handling_unit.doctype,
			handling_unit.name,
			printer_setting,
			print_format,
			handling_unit,
		)


"""
<img src="data:image/png;base64,{{ labelary_api(doc, 'Handling Unit 6x4 ZPL Format', {}) }}" />
"""


def labelary_api(doc, print_format, settings=None):
	if not settings:
		settings = {}
	print_format = frappe.get_doc("Print Format", print_format)
	if print_format.raw_printing != 1:
		frappe.throw("This is a not a RAW print format")
	output = ""
	# using a custom jinja environment so we don't have to use frappe's formatting
	methods, filters = get_jinja_hooks()
	e = Environment(undefined=DebugUndefined)
	e.globals.update(get_safe_globals())
	if methods:
		e.globals.update(methods)
	template = e.from_string(print_format.raw_commands)
	output = template.render(doc=doc)
	url = "http://api.labelary.com/v1/printers/8dpmm/labels/6x4/0/"
	r = requests.post(url, files={"file": output})
	return base64.b64encode(r.content).decode("ascii")
