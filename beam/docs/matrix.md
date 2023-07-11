# Listview Actions
| Scanned Doctype | Listview              | Action | Target |
|-----------------|-----------------------|--------|--------|
|Handling Unit|Delivery Note|route|Delivery Note|
|Handling Unit|Item|route|Item|
|Handling Unit|Packing Slip|route|Packing Slip|
|Handling Unit|Purchase Invoice|route|Purchase Invoice|
|Handling Unit|Purchase Receipt|route|Purchase Receipt|
|Handling Unit|Putaway Rule|filter|item_code|
|Handling Unit|Quality Inspection|filter|handling_unit|
|Handling Unit|Sales Invoice|route|Sales Invoice|
|Handling Unit|Stock Entry|route|Stock Entry|
|Handling Unit|Stock Reconciliation|route|Stock Reconciliation|
|Item|Delivery Note|filter|item_code|
|Item|Item|route|Item|
|Item|Item Price|filter|item_code|
|Item|Packing Slip|filter|item_code|
|Item|Purchase Invoice|filter|item_code|
|Item|Purchase Receipt|filter|item_code|
|Item|Putaway Rule|filter|item_code|
|Item|Quality Inspection|filter|item_code|
|Item|Sales Invoice|filter|item_code|
|Item|Stock Entry|filter|item_code|
|Item|Stock Reconciliation|filter|item_code|
|Item|Warranty Claim|filter|item_code|
|Warehouse|Delivery Note|filter|warehouse|
|Warehouse|Item|filter|default_warehouse|
|Warehouse|Packing Slip|filter|warehouse|
|Warehouse|Purchase Invoice|filter|warehouse|
|Warehouse|Purchase Receipt|filter|warehouse|
|Warehouse|Sales Invoice|filter|warehouse|
|Warehouse|Stock Entry|filter|warehouse|
|Warehouse|Stock Reconciliation|filter|warehouse|
|Warehouse|Warehouse|route|Warehouse|

 --- 

# Form Actions
| Scanned Doctype | Form                  | Action | Target |
|-----------------|-----------------------|--------|--------|
|Handling Unit|Delivery Note|add_or_associate|handling_unit|
|Handling Unit|Delivery Note|add_or_associate|rate|
|Handling Unit|Item Price|set_item_code_and_handling_unit|item_code|
|Handling Unit|Packing Slip|add_or_associate|conversion_factor|
|Handling Unit|Packing Slip|add_or_associate|handling_unit|
|Handling Unit|Packing Slip|add_or_associate|pulled_quantity|
|Handling Unit|Packing Slip|add_or_associate|rate|
|Handling Unit|Packing Slip|add_or_associate|stock_qty|
|Handling Unit|Packing Slip|add_or_associate|warehouse|
|Handling Unit|Purchase Invoice|add_or_associate|handling_unit|
|Handling Unit|Putaway Rule|set_item_code_and_handling_unit|item_code|
|Handling Unit|Quality Inspection|set_item_code_and_handling_unit|item_code|
|Handling Unit|Quality Inspection|set_item_code_and_handling_unit|handling_unit|
|Handling Unit|Sales Invoice|add_or_associate|handling_unit|
|Handling Unit|Stock Entry|add_or_associate|basic_rate|
|Handling Unit|Stock Entry|add_or_associate|conversion_factor|
|Handling Unit|Stock Entry|add_or_associate|handling_unit|
|Handling Unit|Stock Entry|add_or_associate|s_warehouse|
|Handling Unit|Stock Entry|add_or_associate|transfer_qty|
|Handling Unit|Stock Reconciliation|add_or_associate|handling_unit|
|Handling Unit|Warranty Claim|set_item_code_and_handling_unit|item_code|
|Handling Unit|Warranty Claim|set_item_code_and_handling_unit|handling_unit|
|Item|Delivery Note|add_or_increment|item_code|
|Item|Item Price|set_item_code_and_handling_unit|item_code|
|Item|Packing Slip|add_or_increment|item_code|
|Item|Purchase Invoice|add_or_increment|item_code|
|Item|Purchase Receipt|add_or_increment|item_code|
|Item|Putaway Rule|set_item_code_and_handling_unit|item_code|
|Item|Quality Inspection|set_item_code_and_handling_unit|item_code|
|Item|Sales Invoice|add_or_increment|item_code|
|Item|Stock Entry|add_or_increment|item_code|
|Item|Stock Reconciliation|add_or_increment|item_code|
|Item|Warranty Claim|set_item_code_and_handling_unit|item_code|
|Warehouse|Delivery Note|set_warehouse|warehouse|
|Warehouse|Purchase Invoice|set_warehouse|warehouse|
|Warehouse|Purchase Receipt|set_warehouse|warehouse|
|Warehouse|Sales Invoice|set_warehouse|warehouse|
|Warehouse|Stock Entry|set_warehouse|warehouse|
|Warehouse|Stock Reconciliation|set_warehouse|warehouse|
