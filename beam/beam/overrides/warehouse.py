from erpnext.stock.doctype.warehouse.warehouse import Warehouse
from beam.beam.overrides.barcode_mixin import BarcodeMixin


class CustomWarehouse(BarcodeMixin, Warehouse):
	def validate(self):
		super().validate()
