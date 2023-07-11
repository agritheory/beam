# Beam

General Purpose 2D barcode scanning for ERPNext

## What does this application do?

Beam allows you to scan a 2D barcode from either a list view or a form view and help you enter data that would otherwise require a lot of keystrokes. Unlike ERPNext's built-in barcode scanning, Beam expect the user to have a hardware barcode scanner connected to their device.

For example if you scan a barcode associated with an Item in the Item list view, it will take you to that item's record. Read more about how scanning in listviews works [here](./list.md)

If you scan an Item in a Delivery Note, it will populate everything it knows about that item, just as it would if you were to type in the item code. If you scan that item again, it will increment the last row with that item in it.

Read more about scanning in form views [here](./form.md)

## What is a Handling Unit?

A handling unit is an ID for for a stock transaction that allows you to reference everything about it, saved from previous transactions.

A handling unit is generated when materials are received or created in the manufacturing process. So when we want to reference these cloudberries we received in a subsequent transaction, we can scan the handling unit and it will populate the row with all of that data.

Read more about Handling Units [here](./handling_unit.md)


## Installation and Customization

Installation instructions can be found in the [project readme](https://github.com/agritheory/beam)

Beam can be extended with custom hooks both on the server side and in the client. Read more about customization [here](./hooks.md)

## Print Server Integration

Beam offers the ability to print to raw input printers like Zebra printers directly from the browser. Also included are several debugging and example print formats. For more details about configuring this, see the [print server](./print_server.md) section. 

## Roadmap and Planned Features

Feature requests, support requests and bug reports can be made via [GitHub Issues](https://github.com/agritheory/beam/issues).

To test the scanning functionality without actually having a hardware scanner, see the [testing](./testing.md) section.