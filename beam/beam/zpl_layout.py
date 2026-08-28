# Copyright (c) 2026, AgriTheory and contributors
# For license information, please see license.txt

#!/usr/bin/env python3
"""
ZPL Label Layout Tools - Extract coordinates from PDF labels and generate ZPL templates.

Usage:
    python zpl_layout.py /path/to/label.pdf --dpi 300 --width 6 --height 4 --output ./output/
    python zpl_layout.py /path/to/label.pdf --rotate  # Portrait to landscape
"""
import argparse
import json
import sys
from pathlib import Path

import pdfplumber


def analyze_pdf_label(
	pdf_path, target_dpi=300, label_width_inches=6, label_height_inches=4, rotate_90=True
):
	"""
	Extract text blocks with coordinates from PDF and convert to ZPL coordinates.

	Args:
	        pdf_path: Path to PDF file
	        target_dpi: Target printer DPI (default 300)
	        label_width_inches: Label width in inches (landscape)
	        label_height_inches: Label height in inches (landscape)
	        rotate_90: If True, rotate portrait PDF to landscape ZPL

	Returns:
	        Dictionary with text blocks, barcodes, and coordinate mappings
	"""
	results = {
		"label_dimensions": {
			"width_dots": label_width_inches * target_dpi,
			"height_dots": label_height_inches * target_dpi,
			"dpi": target_dpi,
		},
		"text_blocks": [],
		"barcode_regions": [],
		"lines": [],
	}

	with pdfplumber.open(pdf_path) as pdf:
		page = pdf.pages[0]  # First page

		# Get PDF dimensions
		pdf_width = page.width
		pdf_height = page.height

		print(f"PDF dimensions: {pdf_width} x {pdf_height} points")
		print(
			f"Target ZPL: {results['label_dimensions']['width_dots']} x {results['label_dimensions']['height_dots']} dots"
		)
		print(f"Rotation: {'90° CW (portrait → landscape)' if rotate_90 else 'None'}\n")

		# Extract text with coordinates
		words = page.extract_words(x_tolerance=3, y_tolerance=3, keep_blank_chars=False)

		# Group words into text blocks (by proximity)
		text_blocks = []
		current_block = []
		last_y = None
		y_tolerance = 15  # Points tolerance for same line

		for word in words:
			x0, y0, x1, y1 = word["x0"], word["top"], word["x1"], word["bottom"]
			text = word["text"]

			# Convert PDF coordinates to ZPL with optional rotation
			# PDF: origin bottom-left, Y increases upward
			# ZPL: origin top-left, Y increases downward

			if rotate_90:
				# Rotate 90° clockwise: portrait PDF (4"x6") → landscape ZPL (6"x4")
				# New X = old Y (from top)
				# New Y = pdf_width - old X
				pdf_y_from_top = pdf_height - y1  # Convert to top-origin
				zpl_x = int((pdf_y_from_top / pdf_height) * results["label_dimensions"]["width_dots"])
				zpl_y = int(((pdf_width - x0) / pdf_width) * results["label_dimensions"]["height_dots"])
			else:
				# No rotation
				zpl_x = int((x0 / pdf_width) * results["label_dimensions"]["width_dots"])
				zpl_y = int(((pdf_height - y1) / pdf_height) * results["label_dimensions"]["height_dots"])

			# Detect potential barcode patterns
			is_barcode = False
			if text.startswith("(") and ")" in text:
				# GS1 application identifier format like (420)
				is_barcode = True
			elif (
				text.replace(" ", "").replace("-", "").isdigit()
				and len(text.replace(" ", "").replace("-", "")) > 10
			):
				# Long numeric string - likely tracking/serial number
				is_barcode = True

			block_info = {
				"text": text,
				"pdf_coords": {"x": x0, "y": pdf_height - y1, "x1": x1, "y1": pdf_height - y0},
				"zpl_coords": {"x": zpl_x, "y": zpl_y},
				"width": int((x1 - x0) / pdf_width * results["label_dimensions"]["width_dots"]),
				"height": int((y1 - y0) / pdf_height * results["label_dimensions"]["height_dots"]),
				"is_potential_barcode": is_barcode,
			}

			if is_barcode:
				results["barcode_regions"].append(block_info)

			text_blocks.append(block_info)

		results["text_blocks"] = text_blocks

		# Detect horizontal lines (dividers)
		lines = page.lines
		for line in lines:
			if rotate_90:
				# Rotate the line coordinates
				is_horizontal = abs(line["x0"] - line["x1"]) < 2  # Vertical in PDF becomes horizontal in ZPL
				if is_horizontal:
					pdf_y_from_top = pdf_height - line["y0"]
					zpl_y = int(
						((pdf_width - line["x0"]) / pdf_width) * results["label_dimensions"]["height_dots"]
					)
					zpl_x0 = int((pdf_y_from_top / pdf_height) * results["label_dimensions"]["width_dots"])
					zpl_x1 = int(
						((pdf_height - line["y1"]) / pdf_height) * results["label_dimensions"]["width_dots"]
					)
					results["lines"].append(
						{
							"type": "horizontal",
							"zpl_coords": {"x0": min(zpl_x0, zpl_x1), "y": zpl_y, "x1": max(zpl_x0, zpl_x1)},
							"length": abs(zpl_x1 - zpl_x0),
						}
					)
			else:
				if abs(line["y0"] - line["y1"]) < 2:  # Horizontal line
					zpl_y = int(
						((pdf_height - line["y0"]) / pdf_height) * results["label_dimensions"]["height_dots"]
					)
					zpl_x0 = int((line["x0"] / pdf_width) * results["label_dimensions"]["width_dots"])
					zpl_x1 = int((line["x1"] / pdf_width) * results["label_dimensions"]["width_dots"])
					results["lines"].append(
						{
							"type": "horizontal",
							"zpl_coords": {"x0": zpl_x0, "y": zpl_y, "x1": zpl_x1},
							"length": zpl_x1 - zpl_x0,
						}
					)

	return results


def smart_group_text(text_blocks, width, height):
	"""
	Intelligently group text blocks into logical sections based on layout.
	"""
	sections = {}

	# Sort blocks by Y position (top to bottom)
	sorted_blocks = sorted(text_blocks, key=lambda b: (b["zpl_coords"]["y"], b["zpl_coords"]["x"]))

	# Define regions (for 6"x4" = 1800x1200)
	regions = {
		"top_bar": (0, 0, width, 150),  # Top header bar
		"main_addresses": (0, 150, width, 500),  # Address blocks
		"divider_1": (0, 500, width, 550),
		"shipping_info": (0, 550, width, 800),  # Postal/carrier info
		"divider_2": (0, 800, width, 850),
		"product_details": (0, 850, width, 1050),  # PO/SKU/Description
		"bottom_barcodes": (0, 1050, width, height),  # Bottom barcode area
	}

	for region_name, (x0, y0, x1, y1) in regions.items():
		sections[region_name] = []
		for block in sorted_blocks:
			bx = block["zpl_coords"]["x"]
			by = block["zpl_coords"]["y"]
			if x0 <= bx < x1 and y0 <= by < y1:
				sections[region_name].append(block)

	return sections


def generate_layout_map(sections, width, height):
	"""
	Generate a visual ASCII layout map.
	"""
	# Create a grid (scaled down)
	grid_width = 90  # chars
	grid_height = 24  # lines
	scale_x = width / grid_width
	scale_y = height / grid_height

	grid = [[" " for _ in range(grid_width)] for _ in range(grid_height)]

	# Draw borders
	for x in range(grid_width):
		grid[0][x] = "-"
		grid[grid_height - 1][x] = "-"
	for y in range(grid_height):
		grid[y][0] = "|"
		grid[y][grid_width - 1] = "|"

	# Place text blocks
	for section_name, blocks in sections.items():
		for block in blocks:
			x = int(block["zpl_coords"]["x"] / scale_x)
			y = int(block["zpl_coords"]["y"] / scale_y)
			if 1 < x < grid_width - 1 and 1 < y < grid_height - 1:
				if block["is_potential_barcode"]:
					grid[y][x] = "█"
				else:
					grid[y][x] = "·"

	return "\n".join("".join(row) for row in grid)


def print_analysis(analysis, sections):
	"""Print human-readable analysis."""
	print("=" * 80)
	print("LABEL ANALYSIS - ZPL COORDINATE MAPPING")
	print("=" * 80)
	print(
		f"\nLabel dimensions: {analysis['label_dimensions']['width_dots']} x {analysis['label_dimensions']['height_dots']} dots @ {analysis['label_dimensions']['dpi']} DPI"
	)

	print("\n" + "-" * 80)
	print("SECTIONS")
	print("-" * 80)

	for section_name, blocks in sections.items():
		if blocks:
			print(f"\n### {section_name.upper().replace('_', ' ')}")
			for block in blocks:
				print(f"  [{block['zpl_coords']['x']:4d}, {block['zpl_coords']['y']:4d}] \"{block['text']}\"")

	print("\n" + "-" * 80)
	print("HORIZONTAL LINES (Dividers)")
	print("-" * 80)
	for line in analysis["lines"]:
		print(
			f"  Y={line['zpl_coords']['y']:4d}, X=[{line['zpl_coords']['x0']:4d} to {line['zpl_coords']['x1']:4d}], Length={line['length']} dots"
		)

	print("\n" + "-" * 80)
	print("BARCODE REGIONS")
	print("-" * 80)
	for barcode in analysis["barcode_regions"]:
		print(
			f"  [{barcode['zpl_coords']['x']:4d}, {barcode['zpl_coords']['y']:4d}] \"{barcode['text']}\" (size: {barcode['width']}x{barcode['height']} dots)"
		)


def generate_zpl_template(analysis, sections):
	"""Generate a production-ready ZPL template with proper structure."""
	lines = []

	# Header
	dpi = analysis["label_dimensions"]["dpi"]
	width_dots = analysis["label_dimensions"]["width_dots"]
	height_dots = analysis["label_dimensions"]["height_dots"]
	width_inches = width_dots / dpi
	height_inches = height_dots / dpi
	lines.append("{#- Shipping Label - " + f'{width_inches}x{height_inches}" @ {dpi} DPI -#}}')
	lines.append(
		"{%- set label = zebra_zpl_label(width="
		+ str(width_dots)
		+ ", length="
		+ str(height_dots)
		+ ", dpi="
		+ str(dpi)
		+ ") -%}"
	)
	lines.append("")
	lines.append("^XA  {# Start Format #}")
	lines.append(f"^PW{width_dots}  " + "{# Print Width: " + str(width_dots) + " dots #}")
	lines.append(f"^LL{height_dots}  " + "{# Label Length: " + str(height_dots) + " dots #}")
	lines.append("")

	# Top section - may contain store number or routing info
	top_blocks = sections.get("top_bar", [])
	if top_blocks:
		lines.append("{# === TOP BAR SECTION === #}")
		for block in sorted(top_blocks, key=lambda b: b["zpl_coords"]["x"]):
			x, y = block["zpl_coords"]["x"], block["zpl_coords"]["y"]
			text = block["text"]
			lines.append(f"^FO{x},{y}^A0N,40,40^FD{text}^FS")
		lines.append("")

	# Main address section
	addr_blocks = sections.get("main_addresses", [])
	if addr_blocks:
		lines.append("{# === ADDRESS SECTION === #}")
		lines.append("{# Ship From (Left Side) #}")
		lines.append("^FO50,150^A0N,35,35^FDShip From:^FS")
		lines.append("^FO50,200^A0N,28,28^FB700,5,0,L,0^FD{{ doc.ship_from_name }}^FS")
		lines.append("^FO50,250^A0N,28,28^FB700,5,0,L,0^FD{{ doc.ship_from_address }}^FS")
		lines.append("")
		lines.append("{# Ship To (Right Side) #}")
		mid_x = analysis["label_dimensions"]["width_dots"] / 2
		lines.append("^FO950,150^A0N,35,35^FDShip To:^FS")
		lines.append("^FO950,200^A0N,28,28^FB800,5,0,L,0^FD{{ doc.ship_to_name }}^FS")
		lines.append("^FO950,250^A0N,28,28^FB800,5,0,L,0^FD{{ doc.ship_to_address }}^FS")
		lines.append("")

	# Horizontal divider
	lines.append("{# === DIVIDER LINE === #}")
	lines.append("^FO50,500^GB1700,3,3^FS")
	lines.append("")

	# Shipping info section (postal code barcode + carrier info)
	ship_blocks = sections.get("shipping_info", [])
	if ship_blocks:
		lines.append("{# === SHIPPING INFORMATION === #}")
		lines.append("{# Postal Code Barcode (Left) #}")
		lines.append("^FO50,520^A0N,25,25^FD(420) Ship to Postal Code^FS")
		lines.append("^FO100,560^BY3^BCN,100,Y,N^FD(420){{ doc.ship_to_zip }}^FS")
		lines.append("^FO120,680^A0N,30,30^FD(420) {{ doc.ship_to_zip }}^FS")
		lines.append("")
		lines.append("{# Carrier Information (Right) #}")
		lines.append("^FO950,520^A0N,28,28^FDCarrier: {{ doc.carrier }}^FS")
		lines.append("^FO950,560^A0N,28,28^FDPRO#: {{ doc.tracking_number }}^FS")
		lines.append("^FO950,600^A0N,28,28^FDB/L#: {{ doc.bill_of_lading }}^FS")
		lines.append(
			"^FO950,640^A0N,28,28^FDNumber of Cartons: {{ doc.carton_number }} of {{ doc.total_cartons }}^FS"
		)
		lines.append("")

	# Second divider
	lines.append("{# === DIVIDER LINE === #}")
	lines.append("^FO50,800^GB1700,3,3^FS")
	lines.append("")

	# Product details section
	prod_blocks = sections.get("product_details", [])
	if prod_blocks:
		lines.append("{# === PRODUCT DETAILS === #}")
		lines.append("{# Left Column #}")
		lines.append("^FO50,820^A0N,28,28^FDPO #: {{ doc.po_number }}^FS")
		lines.append("^FO50,860^A0N,28,28^FDVendor Part #: {{ doc.vendor_part_number }}^FS")
		lines.append("^FO50,900^A0N,28,28^FDUPC #: {{ doc.upc }}^FS")
		lines.append("^FO50,940^A0N,28,28^FDCarton Qty: {{ doc.carton_qty }}^FS")
		lines.append("")
		lines.append("{# Right Column #}")
		lines.append("^FO950,820^A0N,28,28^FDSKU #: {{ doc.sku }}^FS")
		lines.append("^FO950,860^A0N,28,28^FDSize: {{ doc.size }}^FS")
		lines.append("^FO950,900^A0N,28,28^FDColor: {{ doc.color }}^FS")
		lines.append("^FO950,940^A0N,28,28^FDDescription: {{ doc.description }}^FS")
		lines.append("")

	# Bottom barcode section (SSCC-18)
	barcode_blocks = sections.get("bottom_barcodes", [])
	if barcode_blocks:
		lines.append("{# === BOTTOM SSCC BARCODE === #}")
		lines.append("^FO200,1050^A0N,25,25^FDSSCC^FS")
		lines.append("^FO150,1090^BY3^BCN,100,Y,N^FD{{ doc.sscc_barcode }}^FS")
		lines.append("")

	# End format
	lines.append("^XZ  {# End Format #}")

	return "\n".join(lines)


def process_label(pdf_path, output_dir=None, dpi=300, width=6, height=4, rotate=True):
	"""
	Process a PDF label and generate ZPL template.

	Args:
	        pdf_path: Path to PDF file
	        output_dir: Directory to save outputs (default: creates 'output' next to PDF)
	        dpi: Target printer DPI
	        width: Label width in inches
	        height: Label height in inches
	        rotate: Whether to rotate 90 degrees

	Returns:
	        Dictionary with analysis results
	"""
	pdf_path = Path(pdf_path)

	if not pdf_path.exists():
		raise FileNotFoundError(f"PDF not found: {pdf_path}")

	# Determine output directory
	if output_dir is None:
		output_dir = pdf_path.parent / "output"
	else:
		output_dir = Path(output_dir)

	output_dir.mkdir(parents=True, exist_ok=True)

	print(f"\n{'='*80}")
	print(f"Processing: {pdf_path.name}")
	print(f"{'='*80}\n")

	# Analyze PDF
	analysis = analyze_pdf_label(
		str(pdf_path),
		target_dpi=dpi,
		label_width_inches=width,
		label_height_inches=height,
		rotate_90=rotate,
	)

	# Smart grouping
	sections = smart_group_text(
		analysis["text_blocks"],
		analysis["label_dimensions"]["width_dots"],
		analysis["label_dimensions"]["height_dots"],
	)

	# Print layout map
	print("\nVISUAL LAYOUT MAP")
	print("-" * 80)
	layout_map = generate_layout_map(
		sections, analysis["label_dimensions"]["width_dots"], analysis["label_dimensions"]["height_dots"]
	)
	print(layout_map)
	print()

	# Print analysis
	print_analysis(analysis, sections)

	print("\n" + "=" * 80)
	print("PRODUCTION-READY ZPL TEMPLATE")
	print("=" * 80)
	template = generate_zpl_template(analysis, sections)
	print(template)

	# Save outputs
	base_name = pdf_path.stem.lower().replace(" ", "_")

	# Save template
	template_path = output_dir / f"{base_name}.zpl"
	with open(template_path, "w") as f:
		f.write(template)
	print(f"\n✓ ZPL Template: {template_path}")

	# Save layout map
	layout_path = output_dir / f"{base_name}_layout_map.txt"
	with open(layout_path, "w") as f:
		f.write(layout_map)
	print(f"✓ Layout Map: {layout_path}")

	# Save detailed analysis
	analysis_path = output_dir / f"{base_name}_analysis.json"
	with open(analysis_path, "w") as f:
		json.dump(
			{
				"label_dimensions": analysis["label_dimensions"],
				"sections": {
					k: [
						{"text": b["text"], "coords": b["zpl_coords"], "is_barcode": b["is_potential_barcode"]}
						for b in v
					]
					for k, v in sections.items()
					if v
				},
				"lines": analysis["lines"],
			},
			f,
			indent=2,
		)
	print(f"✓ Analysis JSON: {analysis_path}")

	return analysis


def main():
	parser = argparse.ArgumentParser(
		description="Extract coordinates from PDF labels and generate ZPL templates",
		formatter_class=argparse.RawDescriptionHelpFormatter,
		epilog="""
Examples:
  # Basic usage (assumes portrait PDF to landscape 6x4 @ 300 DPI)
  python zpl_layout.py /path/to/label.pdf

  # Specify output directory
  python zpl_layout.py /path/to/label.pdf --output ./my_output/

  # Custom dimensions (no rotation)
  python zpl_layout.py /path/to/label.pdf --width 4 --height 6 --dpi 203 --no-rotate

  # Process multiple PDFs
  for pdf in label_spec/*/label.pdf; do
    python zpl_layout.py "$pdf"
  done
		""",
	)

	parser.add_argument("pdf", help="Path to PDF label file")
	parser.add_argument("--output", "-o", help="Output directory (default: ./output/ next to PDF)")
	parser.add_argument("--dpi", type=int, default=300, help="Target printer DPI (default: 300)")
	parser.add_argument("--width", type=float, default=6, help="Label width in inches (default: 6)")
	parser.add_argument("--height", type=float, default=4, help="Label height in inches (default: 4)")
	parser.add_argument(
		"--no-rotate", action="store_true", help="Do not rotate portrait to landscape"
	)

	args = parser.parse_args()

	try:
		process_label(
			args.pdf,
			output_dir=args.output,
			dpi=args.dpi,
			width=args.width,
			height=args.height,
			rotate=not args.no_rotate,
		)
		print(f"\n{'='*80}")
		print("Processing complete!")
		print(f"{'='*80}\n")
	except Exception as e:
		print(f"\nError: {e}\n", file=sys.stderr)
		sys.exit(1)


if __name__ == "__main__":
	main()
