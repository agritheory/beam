# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

# Tests for camera scanner component.


from playwright.sync_api import expect


def test_camera_scanner_button_visible(page, setup):
	page.add_init_script(
		"""
		navigator.mediaDevices.enumerateDevices = async () => {
			return [
				{
					kind: 'videoinput',
					deviceId: 'mock-camera-1',
					label: 'Mock Camera',
					groupId: 'mock-group'
				}
			];
		};
	"""
	)

	page.get_by_text("Move").click()
	page.wait_for_url("**/beam#/move")

	page.wait_for_timeout(1000)

	camera_button = page.locator("button:has-text('Open Camera')")
	expect(camera_button).to_be_visible()


def test_camera_scanner_button_hidden(page, setup):
	page.add_init_script(
		"""
		navigator.mediaDevices.enumerateDevices = async () => {
			return []; // No cameras
		};
	"""
	)

	page.get_by_text("Move").click()
	page.wait_for_url("**/beam#/move")

	# Wait for component to check permissions and decide to hide itself
	page.wait_for_timeout(1500)

	# The component should not be visible when no cameras are found
	camera_scanner = page.locator(".camera-scanner")
	expect(camera_scanner).to_have_count(0)


def test_camera_scanner_activates_camera(page, setup):
	page.add_init_script(
		"""
		window.getUserMediaCalled = false;
		window.getUserMediaConstraints = null;

		navigator.mediaDevices.enumerateDevices = async () => {
			return [
				{
					kind: 'videoinput',
					deviceId: 'mock-camera-1',
					label: 'Mock Camera',
					groupId: 'mock-group'
				}
			];
		};

		const originalGetUserMedia = navigator.mediaDevices.getUserMedia.bind(navigator.mediaDevices);
		navigator.mediaDevices.getUserMedia = async (constraints) => {
			window.getUserMediaCalled = true;
			window.getUserMediaConstraints = constraints;
			// Return a minimal fake stream
			const canvas = document.createElement('canvas');
			canvas.width = 640;
			canvas.height = 480;
			return canvas.captureStream(30);
		};
	"""
	)

	page.get_by_text("Move").click()
	page.wait_for_url("**/beam#/move")
	page.wait_for_timeout(1000)

	was_called_before = page.evaluate("window.getUserMediaCalled")
	assert was_called_before == False, "getUserMedia should not be called before clicking button"

	camera_button = page.locator("button:has-text('Open Camera')")
	expect(camera_button).to_be_enabled(timeout=10000)
	
	camera_button.click()
	page.wait_for_timeout(1000)

	was_called_after = page.evaluate("window.getUserMediaCalled")
	assert was_called_after == True, "getUserMedia should be called after clicking 'Open Camera'"

	# Verify correct constraints (should request video with back camera)
	constraints = page.evaluate("window.getUserMediaConstraints")
	assert constraints is not None, "getUserMedia should receive constraints"
	assert "video" in constraints, "Should request video stream"
	assert constraints["video"]["facingMode"] == "environment", "Should request back camera"


def test_camera_scanner_permission_denied(page, setup):
	# Mock camera APIs to simulate permission denial
	page.add_init_script(
		"""
		navigator.mediaDevices.enumerateDevices = async () => {
			return [
				{
					kind: 'videoinput',
					deviceId: 'mock-camera-1',
					label: 'Mock Camera',
					groupId: 'mock-group'
				}
			];
		};

		navigator.mediaDevices.getUserMedia = async (constraints) => {
			const error = new Error('Permission denied');
			error.name = 'NotAllowedError';
			throw error;
		};
	"""
	)

	page.get_by_text("Move").click()
	page.wait_for_url("**/beam#/move")
	page.wait_for_timeout(1000)

	camera_button = page.locator("button:has-text('Open Camera')")
	expect(camera_button).to_be_enabled(timeout=10000)
	
	camera_button.click()

	page.wait_for_timeout(500)

	# Verify error message is displayed
	error_message = page.locator(".error-message")
	expect(error_message).to_be_visible()
	expect(error_message).to_contain_text("Permission denied")
