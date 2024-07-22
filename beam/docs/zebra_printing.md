# Zebra Printing

To create a Zebra print format, you need the following documents:
- A ZPL Print Format made against Doctype that may contain barcodes (Item, Warehouse, Handling Units, etc.) that uses the available Jinja utility functions to generate ZPL code.
- A document Print Format that uses the free Labelary API to convert the above ZPL code and generate a preview of the print output for the linked document.

### ZPL Code Generation

Currently, only three types of printable ZPL data can be generated with utilties within Beam:
- `Text`
- `Barcode`
- `Label`

Beam uses the [py-zebra-zpl](https://github.com/mtking2/py-zebra-zpl) library to generate the above types, as it provides a basic interface to create ZPL code using Python objects. Please refer to the library's documentation for more information on how to use it.

**Note:** Additional ZPL elements (like graphic fields) and commands (text mirroring, character encoding, etc.) can be developed separately and added as text directly to the ZPL Print Format. For more information, visit the [official documentation page](https://supportcommunity.zebra.com/s/article/ZPL-Command-Information-and-DetailsV2?language=en_US) or the [Labelary ZPL Programming Guide](https://labelary.com/zpl.html).

In addition, Beam exposes the following Jinja functions to be used within a Print Format:

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

Generate an encoded Zebra printing label via the free Labelary API. It takes the following arguments:

- `doc`: The document to be printed. Required.
- `print_format`: The ZPL Print Format to be used for generating the label. Required.
- `settings`: Additional settings to be passed to the Labelary API. Allows setting up the following parameters:
  - `dpmm`: The desired print density, in dots per millimeter. Defaults to 8.
  - `width`: The desired label width, in inches. Defaults to 6.
  - `height`: The desired label height, in inches. Defaults to 4.
  - `index`: The label index (base 0). Some ZPL code will generate multiple labels, and this parameter can be used to access these different labels. Defaults to 0.

##### Example
```jinja
<img src="data:image/png;base64,{{ labelary_api(doc, 'Handling Unit 6x4 ZPL Format') }}" />
```

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
