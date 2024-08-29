# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

from beam.beam.scan.config import get_scan_doctypes


def boot_session(bootinfo):
	bootinfo.beam = get_scan_doctypes()
