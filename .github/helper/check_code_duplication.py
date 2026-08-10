#!/usr/bin/env python3
"""Run jscpd with a pinned version to avoid npx jscpd@4 / commander ESM breakage."""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

JSCPD_VERSION = "4.0.5"
JSCPD_IGNORE = (
	"**/node_modules/**,**/.venv/**,**/venv/**,**/__pycache__/**,"
	"**/dist/**,**/build/**,**/*.bundle.js,**/tests/**,**/test_*.py,"
	"**/*_test.py,**/*.test.js,**/*.spec.js,**/fixtures/**,"
	"**/*fixtures.py,**/*.min.js,**/*.min.css,**/migrations/**,**/.git/**,**/.github/**"
)


def main() -> int:
	parser = argparse.ArgumentParser(description="Check for code duplication with jscpd")
	parser.add_argument("--max-clones", type=int, default=60)
	parser.add_argument("--max-percentage", type=float, default=5.0)
	args = parser.parse_args()

	if not shutil.which("npx"):
		print(
			"check_code_duplication: npx not found. Install Node.js or skip this hook.",
			file=sys.stderr,
		)
		return 0

	with tempfile.TemporaryDirectory() as report_dir:
		cmd = [
			"npx",
			f"jscpd@{JSCPD_VERSION}",
			".",
			"--format",
			"python,javascript,typescript",
			"--ignore",
			JSCPD_IGNORE,
			"--min-lines",
			"20",
			"--min-tokens",
			"150",
			"--reporters",
			"json,console",
			"--output",
			report_dir,
			"--threshold",
			"6",
			"--exitCode",
			"0",
		]
		result = subprocess.run(cmd, capture_output=True, text=True)
		print(result.stdout, end="")
		if result.stderr:
			print(result.stderr, end="", file=sys.stderr)

		if result.returncode != 0:
			print(
				f"check_code_duplication: jscpd failed with exit code {result.returncode}",
				file=sys.stderr,
			)
			return result.returncode

		json_report = next(Path(report_dir).rglob("jscpd-report.json"), None)
		if json_report is None:
			return 0

		try:
			with json_report.open() as f:
				data = json.load(f)
			clones = data.get("statistics", {}).get("total", {}).get("clones", 0)
			percentage = float(
				data.get("statistics", {}).get("total", {}).get("percentage") or 0
			)
		except (json.JSONDecodeError, KeyError, OSError):
			return 0

		failed = False
		if clones > args.max_clones:
			print(
				f"Clone count {clones} exceeds threshold of {args.max_clones}",
				file=sys.stderr,
			)
			failed = True
		if percentage > args.max_percentage:
			print(
				f"Duplication {percentage:.1f}% exceeds threshold of {args.max_percentage}%",
				file=sys.stderr,
			)
			failed = True

		return 1 if failed else 0


if __name__ == "__main__":
	sys.exit(main())
