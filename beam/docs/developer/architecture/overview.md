## Beam System Overview

### Component Structure
Beam's Vue.js PWA frontend is built with modular components using the Stonecrop library:

**Core Vue Components:**
- **Scan Components**: Barcode scanning interface components
- **Form Components**: Dynamic form rendering using @stonecrop/aform
- **List Components**: Data listing and filtering components
- **Navigation Components**: PWA navigation and routing
- **Mobile Components**: Touch-optimized mobile interfaces

**Stonecrop Integration:**
- `@stonecrop/beam` - Core Beam-specific components
- `@stonecrop/aform` - Advanced form handling components

### Decision Matrix
Beam's scan matrix system defines actions and responses based on both the barcode scanned and the current context (list view or form). This allows for dynamic behavior based on user interactions.

The response action is determined by:
- **Barcode Type**: Item, Handling Unit, Warehouse, etc.
- **Current Context**: Whether the scan occurs in a list view or a form
- **Target Doctype**: The document type being interacted with
- **Current Document State**: Whether the document is new, draft, or submitted
- **Custom Hooks**: Overrides defined in the `hooks.py` file

The default scan matrix defines the following actions:

**List View Actions:**
- **Filter Actions**: Apply filters to list views based on scanned items
- **Route Actions**: Navigate to specific document views

**Form Actions:**
- **`add_or_increment`**: Add new items or increment existing quantities
- **`add_or_associate`**: Associate scanned items with form fields
- **`set_item_code_and_handling_unit`**: Set item and handling unit fields
- **`set_warehouse`**: Set warehouse fields

### Built-in Functions

**Form Functions:**
- `scan()` - The public API endpoint for handling barcode scans
- `get_barcode_context()` - Resolve barcode to document context
- `get_handling_unit()` - Retrieve handling unit details
- `get_stock_entry_item_details()` - Stock entry specific item processing
- `get_list_action()` - Generate list view actions
- `get_form_action()` - Generate form actions

**Mobile Functions:**
- PWA offline capabilities via Workbox
- OnScan.js integration for barcode scanning
- Vue Toast notifications for user feedback
- Pinia state management for offline data sync
