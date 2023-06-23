# Beam

General Purpose 2D barcode scanning for ERPNext

## What does this application do?

Beam allows you to scan a 2D barcode from either a list view or a form view and help you enter data that would otherwise require a lot of keystrokes.

For example if you scan a barcode associated with an Item in the Item list view, it will take you to that item's record.

If you scan an Item in a Delivery Note, it will populate everything it knows about that item, just as it would if you were to type in the item code. If you scan that item again, it will increment the last row with that item in it.

## What is a Handling Unit?

A handling unit is an ID for for a stock transaction that allows you to reference everything about it, saved from previous transactions.

A handling unit is generated when materials are received or created in the manufacturing process. So when we want to reference these cloudberries we received in a subsequent transaction, we can scan the handling unit and it will populate the row with all of that data.

