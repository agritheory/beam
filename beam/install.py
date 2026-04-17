# Copyright (c) 2025, AgriTheory and contributors
# For license information, please see license.txt

from beam.beam.inventory_dimension import setup_inventory_dimensions


def after_install():
	setup_inventory_dimensions(
		[{"dimension_name": "Handling Unit", "reference_document": "Handling Unit"}]
	)
