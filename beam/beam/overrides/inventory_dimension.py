# Copyright (c) 2024, AgriTheory and contributors
# For license information, please see license.txt

from beam.beam.demand.demand import build_demand_allocation_map
from beam.beam.demand.receiving import reset_build_receiving_map


def reset_demand_map(dimension, method):
	return build_demand_allocation_map()


def reset_receiving_map(dimension, method):
	return reset_build_receiving_map()
