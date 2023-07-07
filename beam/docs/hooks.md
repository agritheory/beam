# Extending Beam with custom hooks

Beam can be extended by adding configurations to your application's `hooks.py`.

To make scanning available on a custom doctype, add a table field for "Item Barcode" directly in the doctype or via customize form. Then add a key that is a peer with "Item" in the example below.

To extend scanning functionality within a doctype, add a key that is a peer with "Delivery Note" in the example below.

```python
# hooks.py

beam_listview = {
	"Item": {
		"Delivery Note": [
			{"action": "filter", "doctype": "Delivery Note Item", "field": "item_code"},
			{"action": "filter", "doctype": "Packed Item", "field": "item_code"}
		],
	}
}

beam_frm = {
	"Item": {
		"Delivery Note": [
			{
				"action": "add_or_increment",
				"doctype": "Delivery Note Item",
				"field": "item_code",
				"target": "target.item_code",
			},
			{
				"action": "add_or_increment",
				"doctype": "Delivery Note Item",
				"field": "uom",
				"target": "target.uom",
			},
		]
	}
}
```
To add a custom javascript function, add the following hook to your apps' hooks.py. An example implementation is available in the source code. 

```python
beam_client = {
	"show_message": "custom_app.show_message"
}

```