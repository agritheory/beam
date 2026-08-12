# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import os
import socket
import subprocess
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from urllib.parse import urlparse

import frappe
from frappe.utils import get_bench_path


@contextmanager
def use_current_db_transaction():
	"""
	Refresh pytest's database transaction so reads see commits from the live bench.

	Browser actions (SAVE, RECEIVE, etc.) commit through the web server. Pytest keeps
	its own transaction scope until rollback/begin.
	"""
	frappe.db.rollback()
	frappe.db.begin()
	yield


def wait_for_docstatus(doctype: str, name: str, expected: int, timeout: float = 20.0) -> None:
	"""Block until the live bench has committed `expected` for this document.

	A browser click returns as soon as the request is sent, but the server keeps
	working: cancelling a Delivery Note reverses stock ledger and GL entries and
	routinely outlasts a fixed sleep. Poll instead of guessing a duration.

	Reads go through db.get_value, not get_doc, because get_doc serves the shared
	redis document cache and would hand back the pre-click copy.
	"""
	deadline = time.monotonic() + timeout
	while True:
		# Each poll needs its own transaction or this connection keeps serving the
		# snapshot it took on the first read and never sees the bench's commit.
		frappe.db.rollback()
		frappe.db.begin()
		actual = frappe.db.get_value(doctype, name, "docstatus")
		if actual == expected:
			return
		if time.monotonic() >= deadline:
			raise AssertionError(
				f"{doctype} {name} is docstatus={actual} after {timeout}s, expected {expected}"
			)
		time.sleep(0.25)


def error_toast_text(page) -> str | None:
	"""Return the text of a visible error toast, or None.

	Several portal forms reject input by firing a toast and returning, leaving the
	DOM otherwise unchanged. Asserting on the expected result then fails with
	"element not found" and throws away the reason the app gave.
	"""
	toast = page.locator(".v-toast__item--error .v-toast__text")
	return toast.first.inner_text() if toast.count() else None


_url_state: dict = {}


def probe_host_port(host: str, port: int, timeout: float = 2.0) -> dict:
	result = {"host": host, "port": port, "dns_resolved": False, "tcp_reachable": False}
	try:
		socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
		result["dns_resolved"] = True
	except socket.gaierror:
		return result

	try:
		with socket.create_connection((host, port), timeout=timeout):
			result["tcp_reachable"] = True
	except OSError:
		pass
	return result


def bench_connection_target(site_config: dict, get_url: str) -> dict:
	parsed = urlparse(get_url)
	scheme = parsed.scheme or "http"
	site_host = parsed.hostname or ""

	host_name = site_config.get("host_name")
	if host_name:
		host_parsed = urlparse(host_name if "://" in host_name else f"http://{host_name}")
		if host_parsed.hostname:
			site_host = host_parsed.hostname

	bench_port = site_config.get("webserver_port")
	if bench_port is not None:
		bench_port = int(bench_port)
	elif parsed.port:
		bench_port = parsed.port
	elif host_name:
		host_parsed = urlparse(host_name if "://" in host_name else f"http://{host_name}")
		bench_port = host_parsed.port
	if bench_port is None:
		bench_port = 443 if scheme == "https" else 80

	return {
		"site_host": site_host,
		"bench_port": bench_port,
		"canonical_url": get_url.rstrip("/"),
	}


def wait_for_bench_http(port: int, timeout: float = 120.0):
	ping_url = f"http://127.0.0.1:{port}/api/method/ping"
	deadline = time.time() + timeout
	last_error = None
	while time.time() < deadline:
		try:
			with urllib.request.urlopen(ping_url, timeout=2) as response:
				if response.status == 200:
					return
		except (urllib.error.URLError, OSError) as error:
			last_error = error
		time.sleep(2)
	raise RuntimeError(f"bench web not ready at {ping_url}: {last_error}")


def start_bench_web_server(port: int):
	bench_path = get_bench_path()
	start_command = f"nohup bench serve --port {port} >> bench_run_logs.txt 2>&1 &"
	if os.environ.get("ACT") == "true" and os.getuid() == 0:
		subprocess.run(
			[
				"runuser",
				"-u",
				"ubuntu",
				"--",
				"env",
				"HOME=/home/ubuntu",
				"bash",
				"-lc",
				f"cd {bench_path} && {start_command}",
			],
			check=True,
		)
	else:
		subprocess.Popen(
			["bash", "-lc", start_command],
			cwd=bench_path,
			start_new_session=True,
		)


def ensure_bench_web_running(timeout: float = 120.0):
	target = bench_connection_target(frappe.get_site_config(), frappe.utils.get_url())
	port = target["bench_port"]
	if probe_host_port("127.0.0.1", port, timeout=1.0).get("tcp_reachable"):
		try:
			wait_for_bench_http(port, timeout=5.0)
			return
		except RuntimeError:
			pass

	helper_script = (
		Path(get_bench_path()) / "apps" / "beam" / ".github" / "helper" / "ensure_bench_web.sh"
	)
	if helper_script.is_file():
		env = {**os.environ, "BENCH_ROOT": get_bench_path(), "BENCH_PORT": str(port)}
		subprocess.run(["bash", str(helper_script)], check=True, env=env)
		return

	start_bench_web_server(port)
	wait_for_bench_http(port, timeout=timeout)


def init_playwright_url_state(base_url: str | None = None) -> dict:
	"""
	Resolve how Playwright should reach the bench.

	The site hostname (e.g. ``pinyon`` / ``test_site``) may resolve for Python via
	``/etc/hosts`` but Chromium still needs ``--host-resolver-rules`` to map the
	canonical hostname to ``127.0.0.1`` while preserving the HTTP ``Host`` header.
	"""
	global _url_state
	site_config = frappe.get_site_config()
	target = bench_connection_target(site_config, frappe.utils.get_url())
	site_host = target["site_host"]
	bench_port = target["bench_port"]
	canonical_url = target["canonical_url"]
	localhost_probe = probe_host_port("127.0.0.1", bench_port)
	hostname_probe = probe_host_port(site_host, bench_port) if site_host else {}
	non_localhost = bool(site_host and site_host not in ("127.0.0.1", "localhost"))

	if non_localhost and localhost_probe.get("tcp_reachable"):
		_url_state = {
			"playwright_base_url": canonical_url,
			"playwright_resolver_map_host": site_host,
		}
	elif site_host and hostname_probe.get("dns_resolved") and hostname_probe.get("tcp_reachable"):
		_url_state = {
			"playwright_base_url": canonical_url,
			"playwright_resolver_map_host": None,
		}
	else:
		_url_state = {
			"playwright_base_url": canonical_url,
			"playwright_resolver_map_host": site_host if non_localhost else None,
		}

	if base_url:
		_url_state["playwright_base_url"] = base_url.rstrip("/")
		_url_state["playwright_resolver_map_host"] = None

	return _url_state


def get_playwright_base_url() -> str:
	if _url_state.get("playwright_base_url"):
		return _url_state["playwright_base_url"]
	return frappe.utils.get_url().rstrip("/")


def login_playwright(page, email: str = "support@agritheory.dev", password: str = "admin"):
	"""Fill the Frappe login form and wait until past /login."""
	import re

	from playwright.sync_api import expect

	base_url = get_playwright_base_url()
	if "/login" not in page.url:
		page.goto(f"{base_url}/login")
	page.get_by_role("textbox", name="Email").fill(email)
	page.get_by_role("textbox", name="Password").fill(password)
	page.get_by_role("button", name="Login").click()
	expect(page).not_to_have_url(re.compile(r"/login"), timeout=20000)


def clear_beam_service_workers(page):
	"""Beam PWA registers SW at scope `/`, which can break Desk `/app` navigations."""
	page.evaluate(
		"""async () => {
			if (!('serviceWorker' in navigator)) return;
			const regs = await navigator.serviceWorker.getRegistrations();
			await Promise.all(regs.map((r) => r.unregister()));
			if (window.caches) {
				const keys = await caches.keys();
				await Promise.all(keys.map((k) => caches.delete(k)));
			}
		}"""
	)


def open_desk_form(page, doctype_slug: str, name: str):
	"""Open a Desk form view (not Beam). Re-auth if redirected to login."""
	from playwright.sync_api import expect

	base_url = get_playwright_base_url()
	clear_beam_service_workers(page)
	url = f"{base_url}/app/{doctype_slug}/{name}"
	page.goto(url, wait_until="domcontentloaded")
	if "/login" in page.url:
		login_playwright(page)
		clear_beam_service_workers(page)
		page.goto(url, wait_until="domcontentloaded")
	expect(page.locator(".form-layout")).to_be_visible(timeout=20000)


def wait_for_beam_list_stable(page, timeout_ms: int = 5000):
	"""Wait until list anchors stop growing (infinite scroll finished a wave)."""
	deadline = time.time() + (timeout_ms / 1000)
	last = -1
	stable_rounds = 0
	while time.time() < deadline:
		count = page.locator("css=a.beam_list-anchor").count()
		if count > 0 and count == last:
			stable_rounds += 1
			if stable_rounds >= 3:
				return count
		else:
			stable_rounds = 0
			last = count
		page.wait_for_timeout(150)
	count = page.locator("css=a.beam_list-anchor").count()
	assert count > 0, "Expected at least one Beam list anchor"
	return count


def open_first_beam_list_row(page, home_label: str, url_pattern: str):
	"""Home tile → first real list row (anchor) → wait for hash route."""
	import re

	from playwright.sync_api import expect

	page.get_by_text(home_label, exact=True).click()
	expect(page.locator("css=a.beam_list-anchor").first).to_be_visible()
	wait_for_beam_list_stable(page)
	page.locator("css=a.beam_list-anchor").first.click()
	expect(page).to_have_url(re.compile(url_pattern), timeout=10000)


def order_id_from_beam_url(url: str) -> str:
	"""Extract doc name from Beam hash routes (#/purchase-receipt/PO) or (?id=SO)."""
	from urllib.parse import parse_qs, urlparse

	fragment = url.split("#", 1)[1] if "#" in url else url
	parsed = urlparse(fragment if "://" in fragment else f"http://beam.local/{fragment.lstrip('/')}")
	query_id = parse_qs(parsed.query).get("id", [None])[0]
	if query_id:
		return query_id
	parts = [p for p in parsed.path.split("/") if p]
	return parts[-1] if parts else ""
