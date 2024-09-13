<!-- Copyright (c) 2024, AgriTheory and contributors
For license information, please see license.txt-->

# Listview

The result of scanning a barcode in the listview depends on several factors:

 - Is the barcode recognized?
 - What doctype is it associated with?

For example, when an Item is scanned while viewing the Item list, the user is routed to the record for that Item:

| Scanned Doctype | Listview              | Action | Target |
|-----------------|-----------------------|--------|--------|
|Item|Item|route|Item|


Another example: If an Item is scanned while viewing the Purchase Receipt list, a filter is added that shows the Delivery Notes with those items:

| Scanned Doctype | Listview              | Action | Target |
|-----------------|-----------------------|--------|--------|
|Item|Purchase Receipt|filter|item_code|


Beam uses a [decision matrix](./matrix.md) to decide what action to take based on what kind of doctype has been scanned.

Custom actions and client side functions can be added by using [hooks](./hooks.md)

