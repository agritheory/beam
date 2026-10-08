<!-- Copyright (c) 2025, AgriTheory and contributors
For license information, please see license.txt-->

# Zebra Printing

<div class="byline">
  Tyler Matteson 2026-02-24
</div>


To create a Zebra print format, you need the following documents:
- A ZPL Print Format made against Doctype that may contain barcodes (Item, Warehouse, Handling Units, etc.) that uses the available Jinja utility functions to generate ZPL code.
- A document Print Format that uses the free Labelary API to convert the above ZPL code and generate a preview of the print output for the linked document.

### ZPL Code Generation

Currently, only three types of printable ZPL data can be generated with utilities within BEAM:
- `Text`
- `Barcode`
- `Label`

BEAM uses the [py-zebra-zpl](https://github.com/mtking2/py-zebra-zpl) library to generate the above types, as it provides a basic interface to create ZPL code using Python objects. Please refer to the library's documentation for more information on how to use it.

**Note:** Additional ZPL elements (like graphic fields) and commands (text mirroring, character encoding, etc.) can be developed separately and added as text directly to the ZPL Print Format. For more information, visit the [official documentation page](https://supportcommunity.zebra.com/s/article/ZPL-Command-Information-and-DetailsV2?language=en_US) or the [Labelary ZPL Programming Guide](https://labelary.com/zpl.html).

In addition, BEAM exposes the following Jinja functions to be used within a Print Format:

---

#### `barcode128`

Generate a [Code 128](https://en.wikipedia.org/wiki/Code_128) barcode image. It takes the following arguments:

- `barcode_text`: The text to be encoded in the barcode. Required.

##### Example
```jinja
{{ barcode128(doc.barcodes[0].barcode) }}
```

---

#### `formatted_zpl_barcode`

Generate a formatted ZPL barcode. It takes the following arguments:

- `barcode_text`: The text to be encoded in the barcode. Required.

##### Example
```jinja
{{ formatted_zpl_barcode(doc.barcodes[0].barcode) }}
```

---

#### `formatted_zpl_label`

Generate a formatted ZPL label object. It takes the following arguments:

- `width`: The width of the label in dots. Required.
  - This value is typically the width of the expected label multiplied by the printer's DPI value.
- `height`: The height of the label in dots. Required.
  - This value is typically the height of the expected label multiplied by the printer's DPI value.
- `dpi`: The dots-per-inch (DPI) value of the printer. Defaults to 203.
  - Visit the [official documentation](https://supportcommunity.zebra.com/s/article/000026166) to determine the DPI for your Zebra printer model.
- `print_speed`: The print speed of the printer in inches per second (ips). Defaults to 2.
  - Slower print speeds typically yield better print quality.
  - Visit the [official documentation](https://supportcommunity.zebra.com/s/article/Setting-the-Print-Speed-via-ZPL) to determine the acceptable print speed values for your Zebra printer model.
- `copies`: The number of copies to print. Defaults to 1.

##### Example
```jinja
{% set label = formatted_zpl_label(width=6*203, height=4*203, dpi=203) %}
{{ label.start }}
<!-- add ZPL elements and commands -->
{{ label.end }}
```

---

#### `formatted_zpl_text`

Generate formatted ZPL text. It takes the following arguments:

- `text`: The text to be printed. Required.
- `width`: The width of the text in dots.

##### Example
```jinja
{{ formatted_zpl_text('Hello, World!', 100) }}
```

---

#### `zebra_zpl_barcode`

Generate a Zebra ZPL `Barcode` object. It takes the following arguments:

- `data`: The text to be encoded in the barcode. Required.

Additional arguments can be passed to the function to customize the barcode. Please refer to the [py-zebra-zpl documentation](https://github.com/mtking2/py-zebra-zpl#usage) for more information.

##### Example
```jinja
{% set label = zebra_zpl_label(width=6*203, length=4*203, dpi=203) -%}
{{ label.add(zebra_zpl_barcode(doc.barcodes[0].barcode)) }}
{{ label.dump_contents() }}
```

---

#### `zebra_zpl_label`

Generate a Zebra ZPL `Label` object. Arguments can be passed to the function to customize the label. Please refer to the [py-zebra-zpl documentation](https://github.com/mtking2/py-zebra-zpl#usage) for more information.

##### Example
```jinja
{% set label = zebra_zpl_label(width=6*203, length=4*203, dpi=203) -%}
{{ label.dump_contents() }}
```

---

#### `zebra_zpl_text`

Generate a Zebra ZPL `Text` object. It takes the following arguments:

- `data`: The text to be printed. Required.

Additional arguments can be passed to the function to customize the text. Please refer to the [py-zebra-zpl documentation](https://github.com/mtking2/py-zebra-zpl#usage) for more information.

##### Example
```jinja
{% set label = zebra_zpl_label(width=6*203, length=4*203, dpi=203) -%}
{{ label.add(zebra_zpl_text('Hello, World!')) }}
{{ label.dump_contents() }}
```

---

#### `labelary_api`

Generate an encoded Zebra printing label preview via the free Labelary API. Converts ZPL code to a PNG image for preview purposes. It takes the following arguments:

- `doc`: The document to be printed. Required.
- `print_format`: The ZPL Print Format to be used for generating the label. Required.
- `settings`: Additional settings to be passed to the Labelary API. Allows setting up the following parameters:
  - `dpmm`: The desired print density, in dots per millimeter. Defaults to 8 (≈203 DPI). Use 12 for 300 DPI printers.
  - `width`: The desired label width, in inches. Defaults to 6.
  - `height`: The desired label height, in inches. Defaults to 4.
  - `index`: The label index (base 0). Some ZPL code will generate multiple labels, and this parameter can be used to access these different labels. Defaults to 0.

**Important:** The `width` and `height` settings **MUST match the label dimensions used in your ZPL format**, otherwise the image will appear stretched or compressed. The `dpmm` setting should also match your printer's DPI.

##### Example: 6x4" label at 203 DPI
```jinja
<img src="data:image/png;base64,{{ labelary_api(doc, 'Handling Unit 6x4 ZPL Format', {'width': 6, 'height': 4, 'dpmm': 8}) }}" />
```

##### Example: 4x6" label at 300 DPI
```jinja
<img src="data:image/png;base64,{{ labelary_api(doc, 'Carton Label 4x6 ZPL Format', {'width': 4, 'height': 6, 'dpmm': 12}) }}" />
```

##### DPI Reference
| Printer Type | DPI | DPMM |
|---|---|---|
| Standard | 203 | 8 |
| High Resolution | 300 | 12 |

---

#### `get_handling_unit`

Get the Handling Unit associated with the document. It takes the following arguments:

- `handling_unit`: The Handling Unit to be associated with the document. Required.
- `parent_doctype`: The parent document type for the Handling Unit.

##### Example
```jinja
{% set handling_unit = get_handling_unit('HU-00001', 'Delivery Note') %}
```

---

#### `add_to_label`

Add text, barcodes, and other printable elements to a ZPL label. It takes the following arguments:

- `label`: The existing ZPL `Label` object to which the element should be added
- `element`: The element to be added to the label. Can be an instance of the following types:
  - `Barcode`
  - `Text`

##### Example
```jinja
{% set label = zebra_zpl_label(width=6*203, length=4*203, dpi=203) -%}
{% set barcode = zebra_zpl_barcode(doc.barcodes[0].barcode) %}
{% add_to_label(label, barcode) %}
{{ label.dump_contents() }}
```

---

## ZPL Label Layout Tools

The ZPL Layout Tools are designed to accelerate the process of creating ZPL label templates by automatically extracting text coordinates from PDF shipping label samples and generating production-ready ZPL templates with correct coordinates.

### Overview

Instead of manually measuring and calculating ZPL dot coordinates for every label element, you can:

1. Run the layout analysis tool against a sample PDF label
2. Get an automatically generated ZPL template with all coordinates mapped
3. Customize as needed for your specific document fields
4. Integrate into BEAM print formats

### Command Line Tool

The layout analysis tool is available as a standalone command-line utility at `beam/beam/zpl_layout.py`.

#### Usage

```bash
# Activate the virtual environment
source /path/to/env/bin/activate
cd /path/to/beam

# Basic usage (assumes portrait PDF, 6x4" landscape output @ 300 DPI)
python beam/beam/zpl_layout.py /path/to/label.pdf

# Specify custom label dimensions
python beam/beam/zpl_layout.py /path/to/label.pdf --width 4 --height 6 --dpi 203

# Disable rotation (for already-landscape PDFs)
python beam/beam/zpl_layout.py /path/to/label.pdf --no-rotate

# Custom output directory
python beam/beam/zpl_layout.py /path/to/label.pdf --output ./my_templates/
```

#### Options

- `pdf`: Path to the PDF file to analyze (required)
- `--output, -o`: Output directory (default: creates `output/` directory next to PDF)
- `--dpi`: Target printer DPI - 203 or 300 (default: 300)
- `--width`: Label width in inches (default: 6)
- `--height`: Label height in inches (default: 4)
- `--no-rotate`: Do not rotate portrait PDF to landscape

### Output Files

For each PDF processed, the tool generates three files in the output directory:

#### 1. `{label_name}.zpl` - Production ZPL Template

A Jinja2-compatible ZPL template with:
- All text coordinates automatically mapped
- Sections organized (addresses, shipping info, product details, barcodes)
- Variable placeholders (e.g., `{{ doc.ship_to_name }}`) ready for customization
- Comments indicating each section and coordinate values

Example:
```jinja
{# Shipping Label - 6.0x4.0" @ 300 DPI #}
{% set label = zebra_zpl_label(width=1800.0, length=1200.0, dpi=300) -%}

^XA  {# Start Format #}
^PW1800.0  {# Print Width: 1800.0 dots #}
^LL1200.0  {# Label Length: 1200.0 dots #}

{# === ADDRESS SECTION === #}
{# Ship From (Left Side) #}
^FO50,150^A0N,35,35^FDShip From:^FS
^FO50,200^A0N,28,28^FB700,5,0,L,0^FD{{ doc.ship_from_name }}^FS
^FO50,250^A0N,28,28^FB700,5,0,L,0^FD{{ doc.ship_from_address }}^FS

...

^XZ  {# End Format #}
```

#### 2. `{label_name}_analysis.json` - Coordinate Data

JSON file containing detailed extraction results:
- Label dimensions in dots and DPI
- Text blocks grouped by section (main_addresses, shipping_info, product_details, etc.)
- Each block includes:
  - Text content
  - ZPL X,Y coordinates (in dots)
  - Barcode detection flag

Use this for reference or further customization.

#### 3. `{label_name}_layout_map.txt` - ASCII Visual Map

ASCII art representation of the label layout showing:
- `·` for regular text blocks
- `█` for detected barcodes
- Borders indicating label dimensions

Useful for visually verifying that coordinates were extracted correctly.

### Integration into BEAM Print Formats

Once you have a generated ZPL template:

1. **Copy the template** into a new BEAM Print Format (create via Settings > Print Format)
2. **Replace variable placeholders** with actual document field references:
   - `{{ doc.ship_from_name }}` → `{{ doc.supplier_name }}` (or your actual field)
   - `{{ doc.po_number }}` → `{{ doc.purchase_order_number }}`
   - etc.
3. **Test in Labelary viewer** at https://labelary.com/viewer.html
   - Copy the ZPL code (with variables replaced by test data)
   - Set label size to match your printer
   - Verify layout and positioning
4. **Adjust coordinates as needed** based on actual print results

### Key Features

- **Automatic Barcode Detection**: Identifies GS1 Application Identifiers (e.g., `(420)`) and long numeric sequences
- **Rotation Support**: Automatically converts portrait PDFs (4"×6") to landscape (6"×4")
- **Multi-DPI Support**: Works with 203 DPI and 300 DPI printers
- **Section Grouping**: Intelligently organizes extracted text into logical regions
- **Visual Feedback**: ASCII layout map shows element positions for verification

### Coordinate System

The tool converts between different coordinate systems:

| System | Origin | Y-Axis | Units | Example |
|--------|--------|--------|-------|---------|
| PDF | Bottom-left | Increases upward | Points | (x0, y0) in pdfplumber |
| ZPL | Top-left | Increases downward | Dots | ^FO{x},{y} in ZPL |

Conversion formula: `zpl_dots = pdf_points × (target_dpi / 72)`

### DPI/DPMM Reference

When using the `labelary_api` helper or generating ZPL templates, ensure label dimensions match across all components:

| DPI | DPMM | Printer Type | Example |
|-----|------|--------------|---------|
| 203 | 8 | Standard Zebra | Most common thermal printers |
| 300 | 12 | High Resolution | Better quality labels |

**Critical:** Always pass the correct `dpmm` value to `labelary_api` to avoid image stretching. If your ZPL template is 6x4" at 300 DPI but you pass `dpmm: 8`, the preview will appear stretched horizontally.

Example configurations:
- 6x4" label at 203 DPI: `labelary_api(doc, 'Format Name', {'width': 6, 'height': 4, 'dpmm': 8})`
- 4x6" label at 300 DPI: `labelary_api(doc, 'Format Name', {'width': 4, 'height': 6, 'dpmm': 12})`

### Troubleshooting

**Coordinates seem incorrect:**
- Verify the PDF orientation (portrait vs. landscape)
- Try with `--no-rotate` flag if PDF is already landscape
- Check that DPI matches your printer specification

**Text not grouped correctly:**
- The section boundaries may need adjustment for non-standard label layouts
- Use the JSON analysis file to see exactly where text was detected
- Consider manually adjusting section coordinates in the generated template

**Missing elements:**
- Some PDF elements (images, lines) may not be extracted
- pdfplumber extracts text only; complex graphics may need manual addition
- Review the layout map to identify missing elements

### Example: Processing Trading Partner Labels

The `label_spec/` folder contains sample PDFs from multiple trading partners. To generate templates for all:

```bash
cd /path/to/beam
source /path/to/env/bin/activate

# Pure Hockey (6x4 with rotation)
python beam/beam/zpl_layout.py label_spec/Pure\ Hockey\ -\ ASN\ label/*.pdf

# Mindware (4x6 already landscape)
python beam/beam/zpl_layout.py "label_spec/Mindware - Oriental Trading Co - Carton label/*.pdf" --width 4 --height 6 --no-rotate
```

Templates are automatically saved to `label_spec/{partner}/output/` for easy access.
