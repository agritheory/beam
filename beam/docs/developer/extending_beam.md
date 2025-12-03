<!-- Copyright (c) 2025, AgriTheory and contributors
For license information, please see license.txt-->

# Extending BEAM

### Schema / Hooks
Beam extends Frappe's hook system with custom hooks for different contexts:

**Beam-specific Hooks:**
- **`beam_client`**: Additional client-side functions
- **`beam_listview`**: Custom list view scan actions
- **`beam_frm`**: Custom form scan actions
- **`beam_mobile`**: Custom mobile-specific components and route definitions
- **`demand`**: Demand planning and forecasting hooks

**Hook Override System:**
```python
# Custom scan actions for forms via hooks
beam_override = frappe.get_hooks("beam_frm")
override_doctype = beam_override.get(barcode_doc.doc.doctype)
override_action = override_doctype.get(context.frm)
```

#### Examples

```python
# hooks.py

# To make scanning available on a custom doctype, add a table field
# for "Item Barcode" directly in the doctype or via customize form.
# Then add a key that is a peer with "Item" in the example below.

# To extend scanning functionality within a doctype, add a key that
# is a peer with "Delivery Note" in the example below.

beam_listview = {
	"Item": {
		"Delivery Note": [
			{
				"action": "filter",
				"doctype": "Delivery Note Item",
				"field": "item_code"
			},
			{
				"action": "filter",
				"doctype": "Packed Item",
				"field": "item_code"
			}
		],
	},
	...
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
	},
	...
}

# To add a custom JavaScript function, use the following hook:
beam_client = {"show_message": "custom_app.show_message"}
```

## Adding Custom Vue Components

- Why
- What
- How

```python
beam_mobile = {
	"components": {
		"Consume": "./custom_app/custom_app/public/js/Consume.vue",
	},
	"routes": [
		{
			"path": "/consume",
			"name": "consume",
			"component": "Consume",
			"meta": {"requiresAuth": True, "doctype": "Stock Entry", "view": "form"},
		},
	],
}

```
