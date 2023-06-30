# Purchase Receipt and Purchase Invoice


# Delivery Note and Sales Invoice


# Stock Entry

## Material Transfer for Manufacture, Material Transfer, Send to Contractor

In a case where the entire quantity associated with a Handling Unit is moved from one warehouse to another, that Handling Unit is reused.

| Item             | Warehouse          | Handling Unit  |       Quantity |
| ---------------- | ------------------ | -------------- | --------------:|
| Cocoplum         | Storeroom          |            123 |         -40 Ea |
| Cocoplum         | Work In Progress   |            123 |          40 Ea |

In a case where less than the total quantity associated with a Handling Unit is moved from one warehouse to another, a new handling unit is generated for the new units. Subsequent scans or lookups of the original handling (123) unit will return the remainder or net quantity.

| Item             | Warehouse          | Handling Unit  |       Quantity |
| ---------------- | ------------------ | -------------- | --------------:|
| Cocoplum         | Storeroom          |            123 |         -20 Ea |
| Cocoplum         | Work In Progress   |            456 |          20 Ea |

## Repack and Manufacture

In the case of a Repack, Material Issue or Material Consumption for Manufacture, a new Handling Unit is generated for the new quantities. 

| Item             | Warehouse          | Handling Unit  |       Quantity |
| ---------------- | ------------------ | -------------- | --------------:|
| Cocoplum         | Storeroom          |            123 |       	 -40 Ea |
| Cocoplum         | Storeroom          |            789 |    1 Box of 40 |


In a case where less than the total quantity associated with a Handling Unit is consumed, subsequent scans or lookups of the original handling (123) unit will return the remainder or net quantity.

| Item             | Warehouse          | Handling Unit  |       Quantity |
| ---------------- | ------------------ | -------------- | --------------:|
| Cocoplum         | Storeroom          |            123 |       	 -20 Ea |
| Cocoplum Puree   | Work In Progress   |            012 |        1 liter |
| Cocoplum         | Scrap              |                |           1 Ea |

TODO: Make a setting on the BOM Scrap Item that toggles if a handling unit should be created

## Material Issue, Material Consumption for Manufacture

In both these cases, there is no offsetting movement or creation of items.

| Item             | Warehouse          | Handling Unit  |       Quantity |
| ---------------- | ------------------ | -------------- | --------------:|
| Cocoplum         | Storeroom          |            123 |         -20 Ea |


| Item             | Warehouse          | Handling Unit  |       Quantity |
| ---------------- | ------------------ | -------------- | --------------:|
| Cocoplum         | Work In Progress   |            123 |         -20 Ea |

## Material Receipt
In the case of Material Receipt, a new Handling Unit is generated for each item. 

| Item             | Warehouse          | Handling Unit  |       Quantity |
| ---------------- | ------------------ | -------------- | --------------:|
| Cocoplum         | Storeroom          |            123 |          20 Ea |