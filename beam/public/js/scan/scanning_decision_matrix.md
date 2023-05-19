# List view actions

| Scanned Doctype | Page                  | Action | Target |
|-----------------|-----------------------|--------|--------|
| Item            | Item List             | Route  | Record |
| Asset           | Item List             | Filter | List   |
| Warehouse       | Item List             | Filter | List   |
| Handling Unit   | Item List             | Filter | List   |
|                 |                       |        |        |
| Item            | Asset List            | Filter | List   |
| Asset           | Asset List            | Route  | Record |
| Warehouse       | Asset List            | None   |        |
| Handling Unit   | Asset List            | None   |        |
|                 |                       |        |        |
| Item            | Warehouse List        | None   |        |
| Asset           | Warehouse List        | None   |        |
| Warehouse       | Warehouse List        | Route  | Record |
| Handling Unit   | Warehouse List        | None   |        |
|                 |                       |        |        |
| Item            | Purchase Receipt List | Filter | List   |
| Asset           | Purchase Receipt List | Filter | List   |
| Warehouse       | Purchase Receipt List | Filter | List   |
| Handling Unit   | Purchase Receipt List | Route  | Record |
|                 |                       |        |        |
| Item            | Purchase Invoice List | Filter | List   |
| Asset           | Purchase Invoice List | Filter | List   |
| Warehouse       | Purchase Invoice List | Filter | List   |
| Handling Unit   | Purchase Invoice List | Route  | Record |
|                 |                       |        |        |
| Item            | Delivery Note List    | Filter | List   |
| Asset           | Delivery Note List    | None   |        |
| Warehouse       | Delivery Note List    | Filter | List   |
| Handling Unit   | Delivery Note List    | Route  | Record |
|                 |                       |        |        |
| Item            | Sales Invoice List    | Filter | List   |
| Asset           | Sales Invoice List    | None   |        |
| Warehouse       | Sales Invoice List    | Filter | List   |
| Handling Unit   | Sales Invoice List    | Route  | Record |
|                 |                       |        |        |
| Item            | Stock Entry List      | Filter | List   |
| Asset           | Stock Entry List      | None   |        |
| Warehouse       | Stock Entry List      | Filter | List   |
| Handling Unit   | Stock Entry List      | Route  | Record |
|                 |                       |        |        |
| Item            | Stock Recon List      | Filter | List   |
| Asset           | Stock Recon List      | None   |        |
| Warehouse       | Stock Recon List      | Filter | List   |
| Handling Unit   | Stock Recon List      | Route  | Record |

# Form/ Doctype Actions

| Scanned Doctype | Page                                      | Action           | Target                      |
|-----------------|-------------------------------------------|------------------|-----------------------------|
| Item            | Purchase Receipt                          | add_or_increment | items                       |
| Asset           | Purchase Receipt                          | add_or_increment | items                       |
| Warehouse       | Purchase Receipt                          | set_warehouse    | items                       |
| Handling Unit   | Purchase Receipt                          | None             |                             |
|                 |                                           |                  |                             |
| Item            | Purchase Invoice                          | add_or_increment | items                       |
| Asset           | Purchase Invoice                          | add_or_increment | items                       |
| Warehouse       | Purchase Invoice                          | set_warehouse    | items                       |
| Handling Unit   | Purchase Invoice                          | add_or_associate | items                       |
|                 |                                           |                  |                             |
| Item            | Delivery Note                             | add_or_increment | items                       |
| Warehouse       | Delivery Note                             | set_warehouse    | items                       |
| Handling Unit   | Delivery Note                             | add_or_associate | items                       |
|                 |                                           |                  |                             |
| Item            | Sales Invoice                             | add_or_increment | items                       |
| Warehouse       | Sales Invoice                             | set_warehouse    | items                       |
| Handling Unit   | Sales Invoice                             | add_or_associate | items                       |
|                 |                                           |                  |                             |
| Item            | Stock Recon                               | add_or_increment | items                       |
| Warehouse       | Stock Recon                               | set_warehouse    | items                       |
| Handling Unit   | Stock Recon                               | add_or_associate | items                       |
|                 |                                           |                  |                             |
| Item            | SE - Material Transfer                    | add_or_increment |                             |
| Warehouse       | SE - Material Transfer                    | set_warehouse    | t_warehouse, to_warehouse   |
| Handling Unit   | SE - Material Transfer                    | add_or_associate |                             |
|                 |                                           |                  |                             |
| Item            | SE - Transfer Manufacture                 | add_or_increment |                             |
| Warehouse       | SE - Transfer Manufacture                 | set_warehouse    | s_warehouse, from_warehouse |
| Handling Unit   | SE - Transfer Manufacture                 | add_or_associate |                             |
|                 |                                           |                  |                             |
| Item            | SE - Manufacture                          | add_or_increment |                             |
| Warehouse       | SE - Manufacture                          | set_warehouse    | t_warehouse, to_warehouse   |
| Handling Unit   | SE - Manufacture                          | add_or_associate |                             |
|                 |                                           |                  |                             |
| Item            | SE - Consumption                          | add_or_increment |                             |
| Warehouse       | SE - Consumption                          | set_warehouse    | s_warehouse, from_warehouse |
| Handling Unit   | SE - Consumption                          | add_or_associate |                             |
|                 |                                           |                  |                             |
| Item            | SE - Repack                               | add_or_increment |                             |
| Warehouse       | SE - Repack                               | set_warehouse    | s_warehouse, from_warehouse |
| Handling Unit   | SE - Repack                               | add_or_associate |                             |
|                 |                                           |                  |                             |
| Item            | SE - Send to Subcontractor                | add_or_increment |                             |
| Warehouse       | SE - Send to Subcontractor                | set_warehouse    | s_warehouse, from_warehouse |
| Handling Unit   | SE - Send to Subcontractor                | add_or_associate |                             |
|                 |                                           |                  |                             |
| Item            | SE - Material Consumption for Manufacture | add_or_increment |                             |
| Warehouse       | SE - Material Consumption for Manufacture | set_warehouse    | s_warehouse, from_warehouse |
| Handling Unit   | SE - Material Consumption for Manufacture | add_or_associate |                             |
