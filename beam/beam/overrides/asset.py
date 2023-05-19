from erpnext.assets.doctype.asset.asset import Asset
from beam.beam.overrides.barcode_mixin import BarcodeMixin


class CustomAsset(BarcodeMixin, Asset):
	def validate(self):
		super().validate()
