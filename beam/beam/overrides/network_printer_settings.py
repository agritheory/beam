# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import re
import shutil
import socket
import subprocess
from contextlib import closing
from pathlib import Path
from urllib.parse import urlparse

import frappe
from frappe import _
from frappe.printing.doctype.network_printer_settings.network_printer_settings import (
	NetworkPrinterSettings,
)

NPS_DOCTYPE = "Network Printer Settings"

RAW_QUEUE_PPD = "raw"
GENERAL_PDF_PPD = "everywhere"
PRINTER_STATE_IDLE = 3
PRINTER_STATE_PROCESSING = 4
PRINTER_STATE_STOPPED = 5
COMMON_PRINTER_OPTIONS = (
	"media",
	"MediaSize",
	"PageSize",
	"sides",
	"Sides",
	"ColorModel",
	"print-quality",
	"PrintQuality",
)


def check_network_printer_settings_read_permission():
	frappe.has_permission(NPS_DOCTYPE, "read", throw=True)


def check_network_printer_settings_write_permission():
	frappe.has_permission(NPS_DOCTYPE, "write", throw=True)


def check_network_printer_settings_create_permission():
	frappe.has_permission(NPS_DOCTYPE, "create", throw=True)


def require_cups():
	try:
		import cups
	except ImportError:
		frappe.throw(
			_(
				"""This feature can not be used as dependencies are missing.
				Please contact your system manager to enable this by installing pycups!"""
			)
		)
	return cups


def cups_connection(server_ip, port):
	cups = require_cups()
	if is_local_cups_server(server_ip, port):
		# HTTP to localhost:631 requires Basic auth; the Unix socket uses peer credentials.
		cups.setServer("")
		cups.setPort(631)
		return cups.Connection()

	cups.setServer(server_ip)
	cups.setPort(int(port))
	return cups.Connection()


def is_local_cups_server(server_ip, port):
	if int(port or 631) != 631:
		return False
	normalized = (server_ip or "").strip().lower()
	return normalized in ("localhost", "127.0.0.1", "::1")


def get_nps_by_printer_name(server_ip, port):
	rows = frappe.get_all(
		"Network Printer Settings",
		filters={"server_ip": server_ip, "port": int(port)},
		fields=["name", "printer_name"],
	)
	return {row.printer_name: row.name for row in rows if row.printer_name}


def default_ppd_for_type(printer_type):
	if printer_type == "Label / RAW":
		return RAW_QUEUE_PPD
	return GENERAL_PDF_PPD


def reject_usb_uri(device_uri):
	if device_uri and device_uri.startswith("usb://"):
		frappe.throw(_("USB printers are not supported."))


def raise_cups_admin_error(exc):
	cups = require_cups()
	if not isinstance(exc, cups.IPPError):
		raise exc

	status = exc.args[0] if exc.args else None
	reason = exc.args[1] if len(exc.args) > 1 else str(exc)
	if status != 4096 and reason != "Unauthorized":
		frappe.throw(_("CUPS error: {0}").format(reason or exc))

	import getpass

	user = getpass.getuser()
	frappe.throw(
		_(
			"CUPS denied this change (Unauthorized). For a local print server, use Server IP localhost. For remote servers, the bench user ({0}) needs lpadmin membership and CUPS must accept the connection: sudo usermod -aG lpadmin {0}"
		).format(user),
		title=_("CUPS Permission Denied"),
	)


def run_cups_admin(action_label, func):
	try:
		return func()
	except Exception as exc:
		cups = require_cups()
		if isinstance(exc, cups.IPPError):
			raise_cups_admin_error(exc)
		frappe.throw(_("Failed to {0}: {1}").format(action_label, exc))


def parse_device_uri_host(device_uri):
	if not device_uri:
		return None
	try:
		parsed = urlparse(device_uri)
		if parsed.hostname:
			return parsed.hostname
	except Exception:
		pass
	match = re.search(r"://([^:/]+)", device_uri)
	if not match:
		return None
	host = match.group(1)
	if host.endswith(".local"):
		return host
	return host


def parse_device_uri_port(device_uri):
	if not device_uri:
		return None
	parsed = urlparse(device_uri)
	if parsed.port:
		return parsed.port
	scheme = (parsed.scheme or "").lower()
	if scheme == "socket":
		return 9100
	if scheme in ("ipp", "ipps"):
		return 631
	if scheme == "http":
		return 80
	if scheme == "https":
		return 443
	return None


def scheme_needs_socket_check(device_uri):
	if not device_uri:
		return False
	scheme = (urlparse(device_uri).scheme or "").lower()
	return scheme in ("socket", "ipp", "ipps", "http", "https", "lpd")


def check_socket_reachable(host, port, timeout=3):
	if not host or not port:
		return False
	try:
		with closing(socket.create_connection((host, int(port)), timeout=timeout)):
			return True
	except OSError:
		return False


def validate_device_uri(device_uri):
	warnings = []
	host = parse_device_uri_host(device_uri)
	port = parse_device_uri_port(device_uri)
	ping_result = (
		ping_host(host)
		if host
		else {"reachable": False, "host": None, "message": _("No host address found in device URI.")}
	)

	socket_reachable = None
	if device_uri and scheme_needs_socket_check(device_uri) and host and port:
		socket_reachable = check_socket_reachable(host, port)

	if device_uri and device_uri.startswith("socket://") and port and port != 9100:
		warnings.append(_("Port {0} is unusual for raw socket printing; expected 9100.").format(port))

	if socket_reachable is False:
		message = _("Cannot connect to {0}:{1}").format(host, port)
	elif socket_reachable is True:
		message = _("Connected to {0}:{1}").format(host, port)
	else:
		message = ping_result.get("message", "")

	reachable = socket_reachable if socket_reachable is not None else ping_result.get("reachable")

	return {
		"host": host,
		"port": port,
		"ping_result": ping_result,
		"socket_reachable": socket_reachable,
		"reachable": reachable,
		"message": message,
		"warnings": warnings,
		"device_uri": device_uri,
	}


def enforce_device_uri_reachable(device_uri):
	result = validate_device_uri(device_uri)
	if device_uri and device_uri.startswith("socket://") and result.get("socket_reachable") is False:
		frappe.throw(result.get("message"))
	return result


@frappe.whitelist()
def test_device_uri(device_uri):
	check_network_printer_settings_read_permission()
	reject_usb_uri(device_uri)
	return validate_device_uri(device_uri)


def normalize_state_reasons(state_reasons):
	if not state_reasons:
		return ""
	if isinstance(state_reasons, (list, tuple)):
		return ", ".join(str(reason) for reason in state_reasons if reason)
	return str(state_reasons)


def map_printer_state_to_indicator(printer_state, state_reasons=None):
	reasons = [
		reason.strip() for reason in normalize_state_reasons(state_reasons).split(",") if reason.strip()
	]
	reason_text = ", ".join(reasons)

	if printer_state == PRINTER_STATE_PROCESSING:
		return {"color": "blue", "label": _("Processing"), "reasons": reason_text}
	if printer_state == PRINTER_STATE_STOPPED:
		label = _("Stopped")
		if any("offline" in reason.lower() for reason in reasons):
			label = _("Offline")
		return {"color": "red", "label": label, "reasons": reason_text}
	return {"color": "green", "label": _("Idle"), "reasons": reason_text}


def get_cups_printer_status_from_attrs(printer):
	if not printer:
		return None

	state = printer.get("printer-state")
	reasons = printer.get("printer-state-reasons", "")
	indicator = map_printer_state_to_indicator(state, reasons)
	accepting = printer.get("printer-is-accepting-jobs")
	if accepting is None:
		accepting = True
	elif isinstance(accepting, str):
		accepting = accepting.lower() in ("true", "1")
	else:
		accepting = bool(accepting)

	return {
		"printer_location": printer.get("printer-location", ""),
		"device_uri": printer.get("device-uri", ""),
		"make_model": printer.get("printer-make-and-model", ""),
		"description": printer.get("printer-info", ""),
		"printer_state": state,
		"printer_state_reasons": reasons,
		"is_accepting_jobs": bool(accepting),
		"is_enabled": state != PRINTER_STATE_STOPPED,
		"indicator_color": indicator["color"],
		"indicator_label": indicator["label"],
		"state_reasons_display": indicator["reasons"],
	}


def build_test_zpl(queue_name, nps_name):
	timestamp = frappe.utils.now_datetime().strftime("%Y-%m-%d %H:%M")
	safe_queue = (queue_name or "").replace("^", "")
	safe_name = (nps_name or "").replace("^", "")
	return (
		f"^XA\n"
		f"^FO50,50^A0N,40,40^FDTest Print^FS\n"
		f"^FO50,100^A0N,30,30^FD{safe_queue}^FS\n"
		f"^FO50,150^A0N,30,30^FD{safe_name}^FS\n"
		f"^FO50,200^A0N,25,25^FD{timestamp}^FS\n"
		f"^XZ\n"
	)


def build_test_text(queue_name, nps_name):
	timestamp = frappe.utils.now_datetime().strftime("%Y-%m-%d %H:%M")
	return _("Test Print\nQueue: {0}\nPrinter: {1}\n{2}").format(queue_name, nps_name, timestamp)


def format_printer_options(conn, printer_name):
	try:
		options = conn.getOptions(printer_name)
	except Exception:
		return {}

	printer_attrs = conn.getPrinters().get(printer_name, {})
	formatted = {}
	for name, choices in options.items():
		if not choices:
			continue
		choice_list = list(choices) if isinstance(choices, (list, tuple)) else [choices]
		current = printer_attrs.get(name, choice_list[0] if choice_list else "")
		formatted[name] = {"current": current, "choices": choice_list}
	return formatted


def classify_fleet_row(cups_queue, cups_attrs, nps_doc=None):
	cups_location = cups_attrs.get("printer-location", "")
	cups_uri = cups_attrs.get("device-uri", "")

	if not nps_doc:
		return {
			"status": _("Orphan Queue"),
			"indicator_color": "orange",
			"cups_queue": cups_queue,
			"nps_name": "",
			"cups_location": cups_location,
			"erpnext_location": "",
			"cups_device_uri": cups_uri,
			"erpnext_device_uri": "",
		}

	nps_location = nps_doc.get("printer_location") or ""
	nps_uri = nps_doc.get("device_uri") or ""
	status = _("Synced")
	indicator_color = "green"

	if nps_location.strip() != cups_location.strip() or nps_uri.strip() != cups_uri.strip():
		status = _("Mismatch")
		indicator_color = "red"

	status_attrs = get_cups_printer_status_from_attrs(cups_attrs) or {}

	return {
		"status": status,
		"indicator_color": indicator_color,
		"cups_queue": cups_queue,
		"nps_name": nps_doc.get("name"),
		"cups_location": cups_location,
		"erpnext_location": nps_location,
		"cups_device_uri": cups_uri,
		"erpnext_device_uri": nps_uri,
		"accepting_jobs": status_attrs.get("is_accepting_jobs"),
		"printer_state": status_attrs.get("indicator_label"),
	}


def get_cups_printer_attrs(conn, printer_name):
	printer = conn.getPrinters().get(printer_name)
	if not printer:
		return None

	try:
		attrs = conn.getPrinterAttributes(printer_name)
		if attrs:
			printer = {**printer, **attrs}
	except Exception:
		pass

	return get_cups_printer_status_from_attrs(printer)


def format_printer_description(make_model, location=""):
	if location and make_model:
		return f"{location} — {make_model}"
	if location:
		return location
	return make_model or ""


def ping_host(host, count=3, timeout=2):
	if not host:
		return {
			"reachable": False,
			"host": None,
			"message": _("No host address found in device URI."),
		}

	if host in ("localhost", "127.0.0.1", "::1"):
		return {
			"reachable": True,
			"host": host,
			"message": _("Print server is local."),
		}

	ping_bin = shutil.which("ping")
	if not ping_bin:
		return {
			"reachable": None,
			"host": host,
			"message": _("ping is not available on this server."),
		}

	try:
		result = subprocess.run(
			[ping_bin, "-c", str(count), "-W", str(timeout), host],
			capture_output=True,
			text=True,
			timeout=(count * timeout) + 5,
			check=False,
		)
		reachable = result.returncode == 0
		message = (
			_("{0} is reachable").format(host)
			if reachable
			else _("{0} did not respond to ping").format(host)
		)
		return {
			"reachable": reachable,
			"host": host,
			"message": message,
			"output": (result.stdout or result.stderr or "")[-500:],
		}
	except subprocess.TimeoutExpired:
		return {
			"reachable": False,
			"host": host,
			"message": _("Ping timed out for {0}").format(host),
		}
	except Exception as exc:
		return {
			"reachable": False,
			"host": host,
			"message": str(exc),
		}


def build_status_indicator(configured, nps_name=None):
	if configured:
		color = "green"
		if nps_name:
			title = _("Configured as {0}").format(nps_name)
		else:
			title = _("Configured in ERPNext")
	else:
		color = "orange"
		title = _("Not configured in ERPNext")
	safe_title = frappe.utils.escape_html(title)
	return f'<span class="indicator {color}" title="{safe_title}"></span>'


def build_status_description(base_description, configured, nps_name=None):
	indicator = build_status_indicator(configured, nps_name)
	if base_description:
		safe_description = frappe.utils.escape_html(base_description)
		return f"{indicator}&nbsp;{safe_description}"
	return indicator


def sort_wizard_entries(entries):
	entries.sort(key=lambda entry: (entry.get("configured"), (entry.get("label") or "").lower()))
	return entries


def safe_get_devices(conn):
	cups = require_cups()
	try:
		try:
			return conn.getDevices(include_schemes=["socket", "ipp", "lpd", "dnssd", "http", "https"])
		except TypeError:
			return conn.getDevices()
	except cups.IPPError:
		return {}
	except Exception:
		return {}


@frappe.whitelist()
def get_wizard_devices(server_ip, port):
	check_network_printer_settings_read_permission()
	conn = cups_connection(server_ip, port)
	nps_lookup = get_nps_by_printer_name(server_ip, port)
	entries = []

	for device_uri, attrs in safe_get_devices(conn).items():
		if device_uri.startswith("usb://"):
			continue
		make_model = attrs.get("device-make-and-model") or attrs.get("device-info") or device_uri
		label = make_model if make_model != device_uri else device_uri.split("/")[-1] or device_uri
		entries.append(
			{
				"value": device_uri,
				"label": label,
				"description": build_status_description(make_model, False),
				"kind": "device",
				"device_uri": device_uri,
				"host": parse_device_uri_host(device_uri),
				"configured": False,
				"nps_name": None,
			}
		)

	printers = conn.getPrinters()
	for printer_id, printer in printers.items():
		make_model = printer.get("printer-make-and-model", "")
		location = printer.get("printer-location", "")
		base_description = format_printer_description(make_model, location)
		configured = printer_id in nps_lookup
		nps_name = nps_lookup.get(printer_id)
		entries.append(
			{
				"value": printer_id,
				"label": printer_id,
				"description": build_status_description(base_description, configured, nps_name),
				"kind": "queue",
				"device_uri": printer.get("device-uri", ""),
				"location": location,
				"host": parse_device_uri_host(printer.get("device-uri", "")),
				"configured": configured,
				"nps_name": nps_name,
			}
		)

	return sort_wizard_entries(entries)


def safe_get_ppds(conn, kwargs=None):
	cups = require_cups()
	kwargs = kwargs or {}
	try:
		return conn.getPPDs(**kwargs) if kwargs else conn.getPPDs()
	except cups.IPPError:
		return {}
	except Exception:
		return {}


@frappe.whitelist()
def get_ppds(server_ip, port, make=None, query=None):
	check_network_printer_settings_read_permission()
	conn = cups_connection(server_ip, port)
	kwargs = {}
	if make:
		kwargs["ppd_make"] = make
	ppds = safe_get_ppds(conn, kwargs)
	results = []
	query_lower = (query or "").lower()

	for ppd_name, attrs in ppds.items():
		make_and_model = attrs.get("ppd-make-and-model") or attrs.get("ppd-make") or ppd_name
		if (
			query_lower
			and query_lower not in make_and_model.lower()
			and query_lower not in ppd_name.lower()
		):
			continue
		results.append(
			{
				"value": ppd_name,
				"label": make_and_model,
				"description": ppd_name,
			}
		)

	if not results:
		for ppd_name, label in (
			(RAW_QUEUE_PPD, "Raw Queue"),
			(GENERAL_PDF_PPD, "Generic IPP Everywhere"),
		):
			if query_lower and query_lower not in label.lower() and query_lower not in ppd_name.lower():
				continue
			results.append({"value": ppd_name, "label": label, "description": ppd_name})

	results.sort(key=lambda row: row["label"].lower())
	return results


@frappe.whitelist()
def validate_wizard_selection(
	server_ip,
	port,
	action,
	printer_name=None,
	device_uri=None,
	kind=None,
):
	check_network_printer_settings_read_permission()
	reject_usb_uri(device_uri)
	nps_lookup = get_nps_by_printer_name(server_ip, port)
	conn = cups_connection(server_ip, port)
	cups_printers = conn.getPrinters()

	if action == "link":
		if kind != "queue":
			return {
				"allowed": False,
				"action": "block",
				"message": _("Select an existing CUPS queue to link."),
			}
		if not printer_name or printer_name not in cups_printers:
			return {
				"allowed": False,
				"action": "block",
				"message": _("Printer not found on the print server."),
			}
		if printer_name in nps_lookup:
			return {
				"allowed": False,
				"action": "block",
				"message": _("Already configured as {0}").format(nps_lookup[printer_name]),
			}
		return {"allowed": True, "action": "link", "message": ""}

	if action == "create":
		if printer_name in cups_printers:
			return {
				"allowed": False,
				"action": "block",
				"message": _("{0} already exists on the print server").format(printer_name),
			}
		if printer_name in nps_lookup:
			return {
				"allowed": False,
				"action": "block",
				"message": _("Already configured as {0}").format(nps_lookup[printer_name]),
			}
		if not device_uri:
			return {"allowed": False, "action": "block", "message": _("A device URI is required.")}
		uri_result = validate_device_uri(device_uri)
		if device_uri.startswith("socket://") and uri_result.get("socket_reachable") is False:
			return {
				"allowed": False,
				"action": "block",
				"message": uri_result.get("message"),
				"warnings": uri_result.get("warnings", []),
			}
		return {
			"allowed": True,
			"action": "create",
			"message": "",
			"warnings": uri_result.get("warnings", []),
		}

	return {"allowed": False, "action": "block", "message": _("Invalid action.")}


@frappe.whitelist()
def create_printer_queue(
	name,
	server_ip,
	port,
	printer_name,
	device_uri,
	ppdname=None,
	printer_location="",
	printer_type="",
):
	check_network_printer_settings_create_permission()
	reject_usb_uri(device_uri)
	validation = validate_wizard_selection(
		server_ip, port, "create", printer_name=printer_name, device_uri=device_uri, kind="device"
	)
	if not validation.get("allowed"):
		frappe.throw(validation.get("message"))

	enforce_device_uri_reachable(device_uri)

	if not ppdname:
		ppdname = default_ppd_for_type(printer_type)

	conn = cups_connection(server_ip, port)
	try:
		conn.addPrinter(
			printer_name,
			ppdname=ppdname,
			info=name,
			location=printer_location or "",
			device=device_uri,
		)
		conn.enablePrinter(printer_name)
		conn.acceptJobs(printer_name)
	except Exception as exc:
		cups = require_cups()
		if isinstance(exc, cups.IPPError):
			raise_cups_admin_error(exc)
		frappe.throw(_("Failed to create printer on print server: {0}").format(exc))

	try:
		doc = frappe.get_doc(
			{
				"doctype": "Network Printer Settings",
				"name": name,
				"server_ip": server_ip,
				"port": int(port),
				"printer_name": printer_name,
				"printer_location": printer_location,
				"printer_type": printer_type,
				"device_uri": device_uri,
			}
		)
		doc.insert()
	except Exception as exc:
		try:
			conn.deletePrinter(printer_name)
		except Exception:
			pass
		frappe.throw(
			_("Printer was created on the print server but ERPNext record failed: {0}").format(exc)
		)

	return doc.as_dict()


@frappe.whitelist()
def link_existing_printer(
	name,
	server_ip,
	port,
	printer_name,
	printer_location="",
	printer_type="",
):
	check_network_printer_settings_create_permission()
	validation = validate_wizard_selection(
		server_ip, port, "link", printer_name=printer_name, kind="queue"
	)
	if not validation.get("allowed"):
		frappe.throw(validation.get("message"))

	conn = cups_connection(server_ip, port)
	printer = conn.getPrinters().get(printer_name, {})
	device_uri = printer.get("device-uri", "")

	doc = frappe.get_doc(
		{
			"doctype": "Network Printer Settings",
			"name": name,
			"server_ip": server_ip,
			"port": int(port),
			"printer_name": printer_name,
			"printer_location": printer_location or printer.get("printer-location", ""),
			"printer_type": printer_type,
			"device_uri": device_uri,
		}
	)
	doc.insert()
	return doc.as_dict()


@frappe.whitelist()
def get_fleet_status(server_ip=None):
	check_network_printer_settings_read_permission()
	servers = frappe.get_all(
		"Network Printer Settings",
		fields=["server_ip", "port"],
		distinct=True,
	)
	if server_ip:
		servers = [row for row in servers if row.server_ip == server_ip]

	rows = []
	seen_servers = set()

	for server in servers:
		key = (server.server_ip, int(server.port))
		if key in seen_servers:
			continue
		seen_servers.add(key)

		nps_rows = frappe.get_all(
			"Network Printer Settings",
			filters={"server_ip": server.server_ip, "port": server.port},
			fields=["name", "printer_name", "printer_location", "device_uri"],
		)
		nps_by_queue = {row.printer_name: row for row in nps_rows if row.printer_name}

		try:
			conn = cups_connection(server.server_ip, server.port)
			cups_printers = conn.getPrinters()
		except Exception as exc:
			rows.append(
				{
					"status": _("Unavailable"),
					"indicator_color": "red",
					"server_ip": server.server_ip,
					"port": server.port,
					"cups_queue": "",
					"nps_name": "",
					"cups_location": "",
					"erpnext_location": "",
					"cups_device_uri": "",
					"erpnext_device_uri": "",
					"accepting_jobs": "",
					"printer_state": str(exc),
				}
			)
			continue

		matched_queues = set()
		for cups_queue, cups_attrs in cups_printers.items():
			matched_queues.add(cups_queue)
			nps_doc = nps_by_queue.get(cups_queue)
			row = classify_fleet_row(cups_queue, cups_attrs, nps_doc)
			row.update({"server_ip": server.server_ip, "port": server.port})
			rows.append(row)

		for nps_doc in nps_rows:
			if nps_doc.printer_name in matched_queues:
				continue
			rows.append(
				{
					"status": _("Missing Queue"),
					"indicator_color": "red",
					"server_ip": server.server_ip,
					"port": server.port,
					"cups_queue": nps_doc.printer_name,
					"nps_name": nps_doc.name,
					"cups_location": "",
					"erpnext_location": nps_doc.printer_location or "",
					"cups_device_uri": "",
					"erpnext_device_uri": nps_doc.device_uri or "",
					"accepting_jobs": "",
					"printer_state": "",
				}
			)

	rows.sort(
		key=lambda row: (
			row.get("server_ip") or "",
			row.get("status") or "",
			row.get("cups_queue") or "",
		)
	)
	return rows


class BEAMNetworkPrinterSettings(NetworkPrinterSettings):
	@frappe.whitelist()
	def get_printers_list(self, ip=None, port=None):
		server_ip = ip if ip is not None else self.server_ip
		server_port = int(port if port is not None else (self.port or 631))
		printer_list = []
		try:
			conn = cups_connection(server_ip, server_port)
			printers = conn.getPrinters()
			for printer_id, printer in printers.items():
				make_model = printer["printer-make-and-model"]
				location = printer.get("printer-location", "")
				description = format_printer_description(make_model, location)
				printer_list.append(
					{
						"value": printer_id,
						"label": printer_id,
						"description": description,
						"location": location,
					}
				)
		except RuntimeError:
			frappe.throw(_("Failed to connect to server"))
		except frappe.ValidationError:
			frappe.throw(_("Failed to connect to server"))
		return printer_list

	@frappe.whitelist()
	def configure_printer_queue(
		self,
		device_uri=None,
		ppdname=None,
		printer_location=None,
		enabled=None,
		accept_jobs=None,
	):
		if not self.printer_name:
			frappe.throw(_("Printer Name is required."))

		reject_usb_uri(device_uri)
		if device_uri:
			enforce_device_uri_reachable(device_uri)
		conn = cups_connection(self.server_ip, self.port)

		def apply_changes():
			if device_uri:
				conn.setPrinterDevice(self.printer_name, device_uri)
				self.device_uri = device_uri

			if ppdname:
				conn.addPrinter(
					self.printer_name,
					ppdname=ppdname,
					info=self.name,
					location=printer_location if printer_location is not None else (self.printer_location or ""),
					device=device_uri
					or self.device_uri
					or conn.getPrinters().get(self.printer_name, {}).get("device-uri", ""),
				)

			if printer_location is not None:
				conn.setPrinterLocation(self.printer_name, printer_location or "")
				self.printer_location = printer_location

			if enabled is not None:
				if frappe.utils.cint(enabled):
					conn.enablePrinter(self.printer_name)
				else:
					conn.disablePrinter(self.printer_name)

			if accept_jobs is not None:
				if frappe.utils.cint(accept_jobs):
					conn.acceptJobs(self.printer_name)
				else:
					conn.rejectJobs(self.printer_name)
			elif enabled is not None and frappe.utils.cint(enabled):
				conn.acceptJobs(self.printer_name)

		run_cups_admin(_("configure printer"), apply_changes)
		self.save()
		return self.as_dict()

	@frappe.whitelist()
	def get_cups_printer_status(self):
		if not self.printer_name:
			frappe.throw(_("Printer Name is required."))

		conn = cups_connection(self.server_ip, self.port)
		status = get_cups_printer_attrs(conn, self.printer_name)
		if not status:
			frappe.throw(_("Printer not found on the print server."))

		return status

	@frappe.whitelist()
	def get_cups_printer_info(self):
		return self.get_cups_printer_status()

	@frappe.whitelist()
	def sync_from_cups(self):
		info = self.get_cups_printer_info()
		self.printer_location = info.get("printer_location") or ""
		if info.get("device_uri"):
			self.device_uri = info["device_uri"]
		self.save()
		return self.as_dict()

	@frappe.whitelist()
	def print_test_page(self):
		if not self.printer_name:
			frappe.throw(_("Printer Name is required."))

		conn = cups_connection(self.server_ip, self.port)
		if self.printer_name not in conn.getPrinters():
			frappe.throw(_("Printer not found on the print server."))

		if self.printer_type == "Label / RAW":
			zpl = build_test_zpl(self.printer_name, self.name)
			file_path = Path(f"/tmp/frappe-zpl-test-{frappe.generate_hash()}.txt")
			file_path.write_text(zpl)
			try:
				job_id = conn.printFile(
					self.printer_name,
					str(file_path),
					_("Test Print"),
					{"document-format": "application/vnd.cups-raw"},
				)
			except Exception as exc:
				frappe.throw(_("Failed to print test label: {0}").format(exc))
			finally:
				file_path.unlink(missing_ok=True)
			return {
				"job_id": job_id,
				"test_type": "zpl",
				"message": _("Test label submitted to {0}").format(self.printer_name),
			}

		try:
			job_id = conn.printTestPage(self.printer_name)
			return {
				"job_id": job_id,
				"test_type": "testpage",
				"message": _("Test page submitted to {0}").format(self.printer_name),
			}
		except Exception:
			text = build_test_text(self.printer_name, self.name)
			file_path = Path(f"/tmp/frappe-text-test-{frappe.generate_hash()}.txt")
			file_path.write_text(text)
			try:
				job_id = conn.printFile(
					self.printer_name,
					str(file_path),
					_("Test Print"),
					{"document-format": "text/plain"},
				)
			except Exception as exc:
				frappe.throw(_("Failed to print test page: {0}").format(exc))
			finally:
				file_path.unlink(missing_ok=True)
			return {
				"job_id": job_id,
				"test_type": "text",
				"message": _("Test page submitted to {0}").format(self.printer_name),
			}

	@frappe.whitelist()
	def get_printer_options(self):
		if not self.printer_name:
			frappe.throw(_("Printer Name is required."))
		if self.printer_type == "Label / RAW":
			return {"options": {}, "message": _("Raw queues have no driver options.")}

		conn = cups_connection(self.server_ip, self.port)
		if self.printer_name not in conn.getPrinters():
			frappe.throw(_("Printer not found on the print server."))

		return {"options": format_printer_options(conn, self.printer_name)}

	@frappe.whitelist()
	def set_printer_options(self, options=None):
		if not self.printer_name:
			frappe.throw(_("Printer Name is required."))
		if self.printer_type == "Label / RAW":
			frappe.throw(_("Raw queues have no driver options."))

		if isinstance(options, str):
			options = frappe.parse_json(options)
		options = options or {}

		conn = cups_connection(self.server_ip, self.port)

		def apply_options():
			conn.setPrinterOptions(self.printer_name, options)

		run_cups_admin(_("update printer options"), apply_options)
		return self.get_printer_options()

	@frappe.whitelist()
	def ping_printer(self):
		if not self.printer_name:
			frappe.throw(_("Printer Name is required."))

		conn = cups_connection(self.server_ip, self.port)
		attrs = get_cups_printer_attrs(conn, self.printer_name)
		if not attrs:
			frappe.throw(_("Printer not found on the print server."))

		device_uri = self.device_uri or attrs.get("device_uri") or ""
		host = parse_device_uri_host(device_uri)
		result = ping_host(host)
		result["device_uri"] = device_uri
		result["cups_location"] = attrs.get("printer_location") or self.printer_location or ""
		result["make_model"] = attrs.get("make_model") or ""
		return result

	@frappe.whitelist()
	def delete_printer_queue(self):
		if not self.printer_name:
			frappe.throw(_("Printer Name is required."))

		conn = cups_connection(self.server_ip, self.port)
		try:
			conn.deletePrinter(self.printer_name)
		except Exception as exc:
			cups = require_cups()
			if isinstance(exc, cups.IPPError):
				raise_cups_admin_error(exc)
			frappe.throw(_("Failed to delete printer from print server: {0}").format(exc))

		frappe.delete_doc("Network Printer Settings", self.name)
		return {"deleted": self.name}

	def validate(self):
		self.push_location_to_cups()

	def push_location_to_cups(self):
		if not self.printer_name:
			return
		try:
			conn = cups_connection(self.server_ip, self.port)
			conn.setPrinterLocation(self.printer_name, self.printer_location or "")
		except Exception as exc:
			frappe.log_error(
				title="CUPS location sync failed",
				message=f"Network Printer Settings {self.name}: {exc}",
			)
