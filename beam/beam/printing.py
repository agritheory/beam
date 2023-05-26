import datetime
import json
import os
from pathlib import Path

import frappe
from frappe.utils import get_bench_path, get_files_path, random_string
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
			e = Environment(undefined=DebugUndefined)
			e.globals.update(get_safe_globals())
			e.globals.update(get_jinja_hooks("methods"))
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
		else:
			handling_unit = frappe.get_doc("Handling Unit", row.get("handling_unit"))
		print_by_server(
			handling_unit.doctype,
			handling_unit.name,
			printer_setting,
			print_format,
			handling_unit,
		)
