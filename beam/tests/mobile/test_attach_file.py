# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

import frappe
from playwright.sync_api import expect

from beam.tests.test_utils import use_current_db_transaction


@pytest.mark.order(10)
def test_upload_photo_to_purchase_receipt(page, setup):
	page.add_init_script(
		"""
		Object.defineProperty(navigator, 'mediaDevices', {
			value: {
				getUserMedia: async (constraints) => {
					const canvas = document.createElement('canvas');
					canvas.width = 640;
					canvas.height = 480;
					const ctx = canvas.getContext('2d');
					ctx.fillStyle = 'blue';
					ctx.fillRect(0, 0, 640, 480);
					return canvas.captureStream(30);
				}
			},
			writable: false,
			configurable: true
		});
	"""
	)

	page.get_by_text("Receive").click()
	page.wait_for_url("**/beam#/receive")
	page.wait_for_timeout(1000)

	page.locator("css=.beam_list-item").first.click()
	page.wait_for_timeout(1000)

	order_id = page.url.split("/")[-1]
	assert order_id

	camera_button = page.locator("button:has-text('Take photo')")
	expect(camera_button).to_be_visible()

	camera_button.click()
	page.wait_for_timeout(1000)

	video_element = page.locator("video.camera-video")
	expect(video_element).to_be_visible()

	# Click capture button to take photo
	capture_button = page.locator(".capture-btn")
	capture_button.click()
	page.wait_for_timeout(1000)

	# Verify photo preview appears
	photo_preview = page.locator(".photos-preview .photo-item")
	expect(photo_preview).to_have_count(1)

	item = page.locator("css=.box .beam_list-item").first
	item_code = item.inner_text().split("\n")[0]

	with use_current_db_transaction():
		barcodes = frappe.get_all(
			"Item Barcode", filters={"parenttype": "Item", "parent": item_code}, pluck="barcode"
		)

	assert len(barcodes) > 0, f"No barcodes found for item {item_code}"

	# Scan the barcode to add item to receipt
	page.evaluate("barcode => scanner.simulate(window, barcode)", barcodes[0])
	page.wait_for_timeout(1000)

	# Click SAVE button to create Purchase Receipt with photo
	save_button = page.locator("button:has-text('SAVE')")
	save_button.click()
	page.wait_for_timeout(1500)

	with use_current_db_transaction():
		receipts = frappe.get_all(
			"Purchase Receipt",
			filters={"docstatus": 0},
			fields=["name"],
			order_by="creation desc",
			limit=1,
		)

	assert len(receipts) > 0, "No Purchase Receipt was created"
	receipt_name = receipts[0]["name"]

	with use_current_db_transaction():
		files = frappe.get_all(
			"File",
			filters={"attached_to_doctype": "Purchase Receipt", "attached_to_name": receipt_name},
			fields=["name", "file_name", "file_url"],
		)

	assert len(files) == 1, f"Expected 1 attached file, found {len(files)}"
	assert files[0]["file_name"].startswith(
		"photo_"
	), f"File name should start with 'photo_', got {files[0]['file_name']}"
	assert files[0]["file_name"].endswith(
		".jpg"
	), f"File should be a .jpg, got {files[0]['file_name']}"
	assert files[0]["file_url"], "File URL should not be empty"
