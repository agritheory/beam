# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt


from playwright.sync_api import expect


def test_camera_button_visible(page, setup):
	page.add_init_script(
		"""
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
		});
	"""
	)

	page.get_by_text("Receive").click()
	page.locator("css=.beam_list-item").first.click()

	page.wait_for_timeout(500)

	camera_button = page.locator("button:has-text('Take photo')")
	expect(camera_button).to_be_visible()


def test_camera_component_hidden(page, setup):
	page.add_init_script(
		"""
		Object.defineProperty(navigator, 'mediaDevices', {
			value: undefined,
			writable: false,
			configurable: true
		});
	"""
	)

	page.get_by_text("Receive").click()
	page.locator("css=.beam_list-item").first.click()

	page.wait_for_timeout(500)

	camera_component = page.locator(".camera-component")
	expect(camera_component).to_have_count(0)


def test_camera_opens_and_closes(page, setup):
	page.add_init_script(
		"""
		Object.defineProperty(navigator, 'mediaDevices', {
			value: {
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
	)

	page.get_by_text("Receive").click()
	page.locator("css=.beam_list-item").first.click()

	page.wait_for_timeout(500)

	camera_button = page.locator("button:has-text('Take photo')")
	camera_button.click()
	page.wait_for_timeout(500)

	video_element = page.locator("video.camera-video")
	expect(video_element).to_be_visible()

	close_camera_button = page.locator(".camera-btn:has-text('Close')")
	expect(close_camera_button).to_be_visible()

	close_camera_button.click()
	page.wait_for_timeout(500)

	expect(close_camera_button).not_to_be_visible()
	expect(camera_button).to_be_visible()
