<!-- Copyright (c) 2026, AgriTheory and contributors
For license information, please see license.txt-->

# BEAM test suite order

Tests use `@pytest.mark.order(N)` with steps of **2** so new tests can slot in without renumbering.
Highest order today: **192** (~71 collected tests).

## Business story (Ambrosia Pie Company)

| Order | Chapter |
|------:|---------|
| 10 | BEAM Settings — handling units enabled |
| 20–28 | Barcodes — Code128 generation, labels, print format |
| 40–48 | Scanning — list/form scan actions, delivery note hooks |
| 60–70 | Receiving & production — purchase receipt through manufacture |
| 71 | Serialized finished goods — serial number scan |
| 72–92 | Outbound & corrections — delivery, invoice, transfer, cancel paths |
| 100–106 | Document printing — `print_by_server` format routing |
| 110–132 | Print server logic — URI, CUPS state, fleet rows, ZPL, notifications |
| 140–162 | Printer setup — wizard, configure, test print, decommission |
| 170–178 | Live CUPS — ZD621 at Chelsea dock (requires local CUPS + lpadmin) |
| 180–192 | Print queue panel — job snapshots, watcher, permissions |

## Running

```bash
cd /path/to/bench
pytest apps/beam/beam/tests -v
```
