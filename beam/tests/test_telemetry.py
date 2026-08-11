# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

"""Opt-in pytest telemetry for diagnosing hangs in CI and ACT.

Enable with BEAM_TEST_TELEMETRY=1 (also auto-enabled when ACT=true).
Periodic stack dumps: BEAM_TEST_STACK_DUMP_SECONDS (default 60).
"""

import faulthandler
import os
import sys
import time

import pytest

ENABLED = (
	os.environ.get("BEAM_TEST_TELEMETRY", "").lower() in ("1", "true", "yes")
	or os.environ.get("ACT") == "true"
)
STACK_DUMP_SECONDS = int(os.environ.get("BEAM_TEST_STACK_DUMP_SECONDS", "60"))


def emit(message):
	if not ENABLED:
		return
	print(f"[beam-test-telemetry {time.strftime('%H:%M:%S')}] {message}", file=sys.stderr, flush=True)


def dump_stacks(reason):
	if not ENABLED:
		return
	emit(f"dumping all thread stacks: {reason}")
	faulthandler.dump_traceback(file=sys.stderr, all_threads=True)


def pytest_configure(config):
	if not ENABLED:
		return
	faulthandler.enable(file=sys.stderr, all_threads=True)
	if STACK_DUMP_SECONDS > 0:
		faulthandler.dump_traceback_later(STACK_DUMP_SECONDS, repeat=True, file=sys.stderr)
	emit(
		"telemetry enabled; "
		f"stderr stack dumps every {STACK_DUMP_SECONDS}s while the process is blocked"
	)


def pytest_runtest_logstart(nodeid, location):
	emit(f"TEST logstart {nodeid} at {location[0]}:{location[1]}")


def pytest_runtest_logfinish(nodeid, location):
	emit(f"TEST logfinish {nodeid}")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_setup(item):
	emit(f"TEST setup begin {item.nodeid}")
	started = time.monotonic()
	yield
	emit(f"TEST setup end {item.nodeid} elapsed={time.monotonic() - started:.3f}s")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_call(item):
	emit(f"TEST call begin {item.nodeid}")
	started = time.monotonic()
	yield
	emit(f"TEST call end {item.nodeid} elapsed={time.monotonic() - started:.3f}s")


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_teardown(item):
	emit(f"TEST teardown begin {item.nodeid}")
	started = time.monotonic()
	yield
	emit(f"TEST teardown end {item.nodeid} elapsed={time.monotonic() - started:.3f}s")


@pytest.hookimpl(hookwrapper=True)
def pytest_fixture_setup(fixturedef, request):
	name = fixturedef.argname
	scope = fixturedef.scope
	node = getattr(request, "node", None)
	nodeid = getattr(node, "nodeid", "?")
	emit(f"FIXTURE setup begin {name} scope={scope} node={nodeid}")
	started = time.monotonic()
	outcome = yield
	status = "ok" if outcome.excinfo is None else "error"
	emit(
		f"FIXTURE setup end {name} scope={scope} "
		f"elapsed={time.monotonic() - started:.3f}s status={status}"
	)


@pytest.hookimpl(hookwrapper=True)
def pytest_fixture_post_finalizer(fixturedef):
	name = fixturedef.argname
	scope = fixturedef.scope
	emit(f"FIXTURE teardown begin {name} scope={scope}")
	started = time.monotonic()
	yield
	emit(f"FIXTURE teardown end {name} scope={scope} " f"elapsed={time.monotonic() - started:.3f}s")


# pytest_plugins entry in conftest loads this module.
