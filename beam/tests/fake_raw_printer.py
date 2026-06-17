# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

import socket
import threading
import time
from contextlib import contextmanager


class FakeRawPrinter:
	def __init__(self, host="127.0.0.1", port=0):
		self.host = host
		self.port = port
		self.received_payloads = []
		self.server = None
		self.thread = None

	@property
	def uri(self):
		return f"socket://{self.host}:{self.port}"

	def start(self):
		self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self.server.bind((self.host, self.port))
		self.server.listen(5)
		self.port = self.server.getsockname()[1]
		self.thread = threading.Thread(target=self.serve, daemon=True)
		self.thread.start()

	def serve(self):
		while True:
			try:
				conn, _addr = self.server.accept()
			except OSError:
				break
			with conn:
				payload = b""
				while True:
					chunk = conn.recv(4096)
					if not chunk:
						break
					payload += chunk
				if payload:
					self.received_payloads.append(payload)

	def stop(self):
		if self.server:
			self.server.close()
			self.server = None
		if self.thread:
			self.thread.join(timeout=2)
			self.thread = None

	def wait_for_payload(self, timeout=5):
		deadline = time.time() + timeout
		while time.time() < deadline:
			if self.received_payloads:
				return self.received_payloads[-1]
			time.sleep(0.1)
		return b""

	def last_text(self):
		payload = self.received_payloads[-1] if self.received_payloads else b""
		return payload.decode("utf-8", errors="replace")

	def clear(self):
		self.received_payloads = []


@contextmanager
def fake_raw_printer(host="127.0.0.1", port=0):
	printer = FakeRawPrinter(host=host, port=port)
	printer.start()
	try:
		yield printer
	finally:
		printer.stop()
