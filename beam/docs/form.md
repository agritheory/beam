## Form

The result of scanning a barcode in the form depends on several factors:

 - Is the barcode recognized?
 - What doctype is it associated with?

For example, when an Item is scanned while viewing a Delivery Note record, it will add a row for that item if one doesn't exist, or increment the highest-indexed existing row with that Item's item_code in it.

| Scanned Doctype | Form                  | Action | Target |
|-----------------|-----------------------|--------|--------|
|Item|Delivery Note|add_or_increment|item_code|

Beam uses a [decision matrix](./matrix.md) to decide what action to take based on what kind of doctype has been scanned.

Custom actions and client side functions can be added by using [hooks](./hooks.md).

