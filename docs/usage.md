# Usage reference

---

## `mfaudit` — main audit runner

```bash
mfaudit [options]
```

### Required arguments

| Argument | Description |
|---|---|
| `--controls FILE [FILE …]` | One or more controls YAML files. Controls from all files are merged before execution. |

### Optional arguments

| Argument | Default | Description |
|---|---|---|
| `--out DIR` | current directory | Output directory. Created automatically if it does not exist. |
| `--irrdbu00 PATH` | `./IRRDBU00` | Path to the IRRDBU00 database unload. |
| `--setropts PATH` | `./SETROPTS` | Path to the REXX-produced SETROPTS export. |
| `--dcollect PATH` | *(not loaded)* | Path to a DCOLLECT output file. Required only by controls that use it. |
| `--system-name NAME` | `UNKNOWN` | Mainframe system identifier shown in the report header. |
| `--report-date DATE` | Today's date | ISO-format date (`YYYY-MM-DD`) shown in the report header. |
| `--template NAME\|FILE` | `default` | Bundled template short name (e.g. `terminal`) or path to a `.html.j2` file. |
| `--format CSV,PDF,JSON` | `CSV,PDF` | Comma-separated output formats to generate. Supported values: `CSV`, `PDF`, `JSON`. |
| `--list-templates` | — | Print available bundled template names and exit. |
| `--anonymize` | off | Replace all RACF user, group, and profile names with stable labels before writing output. Useful when sharing reports externally. |
| `--list-controls` | — | Print paths of bundled controls YAML files and exit. |

### Examples

```bash
# Minimal — outputs written to current directory
mfaudit --controls controls.yaml

# CSV only
mfaudit --controls controls.yaml \
         --format CSV

# JSON only
mfaudit --controls controls.yaml \
         --format JSON

# CSV + JSON + PDF
mfaudit --controls controls.yaml \
         --format CSV,JSON,PDF

# Multiple control files merged, explicit output directory
mfaudit --controls controls.yaml example_controls.yaml \
         --out out/

# All options
mfaudit --irrdbu00 /exports/IRRDBU00 \
         --setropts  /exports/SETROPTS \
         --controls  controls.yaml \
         --system-name PROD1 \
         --report-date 2026-05-17 \
         --format CSV,JSON,PDF \
         --anonymize \
         --out /reports/2026-05-17/
```

### Output files

| File | Description |
|---|---|
| `report.pdf` | PDF report generated when `PDF` is included in `--format` |
| `controls_results.csv` | One row per control: ID, title, status, detail |
| `controls_results.json` | JSON export containing the same control result data as the CSV output |

### Control status values

| Status | Meaning |
|---|---|
| **PASS** | All assertions satisfied |
| **FAIL** | One or more assertions failed; findings listed in report |
| **REVIEW** | Requires human judgment (e.g. list of TRUSTED STCs to verify) |
| **SKIP** | Required data source was not supplied — not counted as a failure |
| **ERROR** | Control logic raised an exception — check the console for the traceback |