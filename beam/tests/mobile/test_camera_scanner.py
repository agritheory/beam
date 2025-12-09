# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

# Tests for camera scanner component.

import pytest

import frappe
from playwright.sync_api import expect


def test_camera_scanner_button_visible(page, setup):
	page.add_init_script("""
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
	""")

	page.get_by_text("Move").click()
	page.wait_for_url("**/beam#/move")

	page.wait_for_timeout(1000)

	camera_button = page.locator("button:has-text('Open Camera')")
	expect(camera_button).to_be_visible()


def test_camera_scanner_button_hidden(page, setup):
	page.add_init_script("""
		navigator.mediaDevices.enumerateDevices = async () => {
			return []; // No cameras
		};
	""")

	page.get_by_text("Move").click()
	page.wait_for_url("**/beam#/move")

	page.wait_for_timeout(1000)

	camera_scanner = page.locator(".camera-scanner")
	expect(camera_scanner).not_to_be_visible()


def test_camera_scanner_permission_denied(page, setup):
	# Mock camera APIs to simulate permission denial
	page.add_init_script("""
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
	""")

	page.get_by_text("Move").click()
	page.wait_for_url("**/beam#/move")
	page.wait_for_timeout(1000)

	camera_button = page.locator("button:has-text('Open Camera')")
	camera_button.click()

	page.wait_for_timeout(500)

	# Verify error message is displayed
	error_message = page.locator(".error-message")
	expect(error_message).to_be_visible()
	expect(error_message).to_contain_text("Permission denied")
