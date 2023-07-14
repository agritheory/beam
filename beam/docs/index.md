# Beam

Beam is a general purpose 2D barcode scanning application for ERPNext.

## What does this application do?

Beam allows a user to scan a 2D barcode from either a listview or a form view, then helps enter data that would otherwise require a lot of keystrokes. Unlike ERPNext's built-in barcode scanning, Beam expects the user to have a hardware barcode scanner connected to their device.

For example, if the user scans a barcode associated with an Item in the Item listview, it will take them to that item's record. Read more about [how scanning in listviews works](./listview.md).

If the user scans an Item in a Delivery Note, it will populate everything it knows about that item, just as it would if they were to type in the item code. If they scan that item again, it will increment the last row with that item in it.

Read more about [how scanning in form views works](./form.md).

## What is a Handling Unit?

A handling unit is the combination of a container, any packaging material, and the items wihin or on it. This could be a pallet of raw materials used in a manufacturing process, a crate containing several other handling units, or an entire warehouse.

Handling units have unique, scannable identification numbers that are used in any stock transaction involving the items contained within the unit. The ID allows the user to reference everything about the stock transaction, saved from previous transactions.

A handling unit is generated when materials are received or created in the manufacturing process.

Read more [about Handling Units here](./handling_unit.md).

## Installation and Customization

Beam comes packed with features, but can be extended with custom hooks both on the server side and in the client as needed. See the following pages for detailed instructions on installing and customizing the application:

- [Installation](https://github.com/agritheory/beam)
- [Customization](./hooks.md)

## Print Server Integration

Beam offers the ability to print to raw input printers like Zebra printers directly from the browser. Also included are several debugging and example print formats. For more details about configuring this, see the [print server section](./print_server.md). 

## Roadmap and Planned Features

Feature requests, support requests and bug reports can be made via [GitHub Issues](https://github.com/agritheory/beam/issues).

To test the scanning functionality without actually having a hardware scanner, see the [testing section](./testing.md).
