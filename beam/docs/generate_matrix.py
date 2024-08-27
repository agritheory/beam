from pathlib import Path


def generate_matrix():
	from beam.beam.scan import frm, listview

	output = "# Listview Actions\n"
	output += "| Scanned Doctype | Listview              | Action | Target |\n"
	output += "|-----------------|-----------------------|--------|--------|\n"

	for doctype, listviews in listview.items():
		for lv, actions in listviews.items():
			for action in actions:
				output += f"|{doctype}|{lv}|{action.get('action')}|{action.get('field')}|\n"

	output += "\n --- \n\n"
	output += "# Form Actions\n"
	output += "| Scanned Doctype | Form                  | Action | Target |\n"
	output += "|-----------------|-----------------------|--------|--------|\n"

	for doctype, forms in frm.items():
		for form, actions in forms.items():
			for action in actions:
				output += f"|{doctype}|{form}|{action.get('action')}|{action.get('field')}|\n"

	filepath = Path(__file__).parent / "matrix.md"

	with filepath.open("w", encoding="utf-8") as f:
		f.write(output)
