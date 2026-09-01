# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

pytest_plugins = ["beam.tests.playwright_fixtures"]

# Tests for the global camera component (barcode scan + optional photo capture).

import pytest
from playwright.sync_api import expect

from beam.tests.playwright_utils import open_first_beam_list_row

# Playwright hits http://<site>:port — not a secure context. Camera.vue hides the FAB
# unless window.isSecureContext is true; force it for positive-path tests.
SECURE_CAMERA_CONTEXT = """
	Object.defineProperty(window, 'isSecureContext', {
		value: true,
		configurable: true,
	});
"""

MOCK_CAMERA_DEVICES = """
	Object.defineProperty(navigator, 'mediaDevices', {
		value: {
			enumerateDevices: async () => {
				return [
					{
						kind: 'videoinput',
						deviceId: 'mock-camera-1',
						label: 'Mock Camera',
						groupId: 'mock-group'
					}
				];
			},
			getUserMedia: async (constraints) => {
				const canvas = document.createElement('canvas');
				canvas.width = 640;
				canvas.height = 480;
				return canvas.captureStream(30);
			}
		},
		writable: false,
		configurable: true
	});
"""


def apply_init_script(page, script):
	"""Register `script` and reload so it actually runs.

	Init scripts only execute on document load, and the login fixture has
	already navigated to /beam by the time a test body runs. Beam's routes are
	hash-based, so clicking a tile never loads a document — without this reload
	the script would never apply.
	"""
	page.add_init_script(script)
	page.reload()


@pytest.mark.order(350)
def test_camera_fab_hidden_on_insecure_origin(page, setup):
	apply_init_script(
		page,
		"""
		Object.defineProperty(window, 'isSecureContext', {
			value: false,
			configurable: true,
		});
	""",
	)

	page.get_by_text("Move").click()
	page.wait_for_url("**/beam#/move")
	page.wait_for_timeout(1500)

	expect(page.locator(".camera-panel")).to_have_count(0)


@pytest.mark.order(351)
def test_camera_fab_visible(page, setup):
	apply_init_script(page, SECURE_CAMERA_CONTEXT + MOCK_CAMERA_DEVICES)

	page.get_by_text("Move").click()
	page.wait_for_url("**/beam#/move")
	page.wait_for_timeout(1000)

	camera_button = page.get_by_role("button", name="Open camera")
	expect(camera_button).to_be_visible()


@pytest.mark.order(352)
def test_camera_opens_stream_for_scan(page, setup):
	apply_init_script(
		page,
		SECURE_CAMERA_CONTEXT
		+ """
		window.getUserMediaCalled = false;
		window.getUserMediaConstraints = null;

		Object.defineProperty(navigator, 'mediaDevices', {
			value: {
				enumerateDevices: async () => {
					return [
						{
							kind: 'videoinput',
							deviceId: 'mock-camera-1',
							label: 'Mock Camera',
							groupId: 'mock-group'
						}
					];
				},
				getUserMedia: async (constraints) => {
					window.getUserMediaCalled = true;
					window.getUserMediaConstraints = constraints;
					const canvas = document.createElement('canvas');
					canvas.width = 640;
					canvas.height = 480;
					return canvas.captureStream(30);
				}
			},
			writable: false,
			configurable: true
		});
	""",
	)

	page.get_by_text("Move").click()
	page.wait_for_url("**/beam#/move")
	page.wait_for_timeout(2000)

	was_called_before = page.evaluate("window.getUserMediaCalled")
	assert was_called_before == False, "getUserMedia should not be called before opening camera"

	camera_button = page.get_by_role("button", name="Open camera")
	expect(camera_button).to_be_enabled(timeout=10000)
	camera_button.click()
	page.wait_for_timeout(1000)

	was_called_after = page.evaluate("window.getUserMediaCalled")
	assert was_called_after == True, "getUserMedia should be called after opening camera"

	constraints = page.evaluate("window.getUserMediaConstraints")
	assert constraints is not None, "getUserMedia should receive constraints"
	assert "video" in constraints, "Should request video stream"


@pytest.mark.order(353)
def test_camera_permission_denied(page, setup):
	apply_init_script(
		page,
		SECURE_CAMERA_CONTEXT
		+ """
		Object.defineProperty(navigator, 'mediaDevices', {
			value: {
				enumerateDevices: async () => {
					return [
						{
							kind: 'videoinput',
							deviceId: 'mock-camera-1',
							label: 'Mock Camera',
							groupId: 'mock-group'
						}
					];
				},
				getUserMedia: async (constraints) => {
					const error = new Error('Permission denied');
					error.name = 'NotAllowedError';
					throw error;
				}
			},
			writable: false,
			configurable: true
		});
	""",
	)

	page.get_by_text("Move").click()
	page.wait_for_url("**/beam#/move")
	page.wait_for_timeout(2000)

	camera_button = page.get_by_role("button", name="Open camera")
	expect(camera_button).to_be_enabled(timeout=10000)
	camera_button.click()
	page.wait_for_timeout(500)

	error_message = page.locator(".error-message")
	expect(error_message).to_be_visible()
	expect(error_message).to_contain_text("Permission denied")


@pytest.mark.order(354)
def test_camera_photo_mode_on_purchase_receipt(page, setup):
	apply_init_script(page, SECURE_CAMERA_CONTEXT + MOCK_CAMERA_DEVICES)

	open_first_beam_list_row(page, "Receive", r"purchase-receipt/")
	page.wait_for_timeout(500)

	camera_button = page.get_by_role("button", name="Open camera")
	expect(camera_button).to_be_visible()
	camera_button.click()
	page.wait_for_timeout(500)

	expect(page.get_by_role("tab", name="Photo")).to_be_visible()
	expect(page.get_by_role("tab", name="Scan")).to_be_visible()
