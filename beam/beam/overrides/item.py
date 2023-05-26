from erpnext.stock.doctype.item.item import Item

from beam.beam.overrides.barcode_mixin import BarcodeMixin


class CustomItem(BarcodeMixin, Item):
	def validate(self):
		super().validate()
