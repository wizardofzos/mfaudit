<p align="center">
  <img src="images/mfaudit-logo.png" alt="MFAudit logo" width="320">
</p>

# MFAudit

**Automated RACF security auditing — from raw RACF exports to audit-ready reports in a single command.**

MFAudit reads standard z/OS security exports — IRRDBU00 unloads, SETROPTS
exports, optional DCOLLECT data, and runtime library inventories — and evaluates
them against a library of CIS Benchmark and custom RACF security controls.

The result:

- styled PDF reports;
- CSV exports;
- JSON exports;
- deterministic PASS / FAIL / REVIEW verdicts;
- optional anonymized output for external sharing.

---

## What you get

| | |
|---|---|
| **46+ CIS controls** | Password policy, class activation, STARTED tasks, Unix System Services, Db2, CICS |
| **Custom controls** | Write organization-specific controls in YAML |
| **PDF reports** | Human-readable audit reports with findings and summaries |
| **CSV exports** | Spreadsheet, SIEM, or dashboard ingestion |
| **JSON exports** | API, Splunk, Elastic, automation, and pipeline integration |
| **Anonymized reports** | Replace RACF identifiers with stable pseudonymous labels |

---

## Quick start

```bash
# 1  Collect data on z/OS
#    Copy SETROPTS and IRRDBU00 to your workstation

# 2  Install MFAudit
pip install mfaudit

# 3  Run the audit (bundled CIS controls used by default)
mfaudit

# 4  Open the PDF report
open report.pdf             # macOS
xdg-open report.pdf         # Linux
start report.pdf            # Windows
```

Default behavior:

- `--setropts ./SETROPTS`
- `--irrdbu00 ./IRRDBU00`
- `--format CSV,PDF`

Controls requiring missing data sources are automatically marked as `SKIP`.

---

## Output formats

MFAudit supports multiple output formats simultaneously.

### Default outputs

```bash
mfaudit
```

Generated files:

```text
report.pdf
controls_results.csv
```

### JSON output

```bash
mfaudit --format JSON
```

Generated files:

```text
controls_results.json
```

### All output formats

```bash
mfaudit --format CSV,JSON,PDF
```

Generated files:

```text
report.pdf
controls_results.csv
controls_results.json
```

Supported values:

| Format | Output |
|---|---|
| `PDF` | `report.pdf` |
| `CSV` | `controls_results.csv` |
| `JSON` | `controls_results.json` |

---

## Data flow

```text
z/OS system
  ├── IRRDBU00 unload ───────────────────────────────────┐
  ├── SETROPTS export ─────────────────────────────────┐ │
  ├── DCOLLECT (optional) ────────────────────────────┐ │ │
  └── runtime inventory (optional) ─────────────────┐ │ │ │
                                                    ↓ ↓ ↓ ↓
  controls YAML ────────────────────────────►   mfaudit
                                                   │
                                                   ├── report.pdf
                                                   ├── controls_results.csv
                                                   └── controls_results.json
```

The runtime inventory can supply active APF, PARMLIB, PROCLIB, LPA, master
catalog, and RACF database data sets plus approved system-programmer IDs. See
the [quick start](quickstart.md#optional-runtime-inventory) for its YAML format
and the [usage reference](usage.md#runtime-list-and-inventory-format) for all
individual input flags.

---

## Anonymized reporting

Generate reports safe for external sharing:

```bash
mfaudit --format CSV,JSON,PDF \
         --anonymize
```

Example anonymized identifiers:

```text
USR-0001
GRP-0042
PRF-0017
```

Mappings remain stable within the same execution run so findings stay readable and correlatable.

---

## Repository layout

```text
controls.yaml              CIS Benchmark controls
example_controls.yaml      Example custom controls
mfaudit/                   Python package and CLI
templates/                 Bundled PDF report templates
docs/                      Documentation (MkDocs)
```

---

## Templates

Bundled report templates:

| Template | Style |
|---|---|
| `default` | Light corporate report |
| `terminal` | Green phosphor 3270-style terminal theme |

Example:

```bash
mfaudit --template terminal
```

List available templates:

```bash
mfaudit --list-templates
```

---

## Installation

```bash
pip install mfaudit
```

Optional xhtml2pdf fallback renderer:

```bash
pip install "mfaudit[pdf-xhtml]"
```

See the installation guide for:

- Linux/macOS/Windows dependencies;
- GTK/WeasyPrint requirements;
- development installation;
- editable installs.

---

## Use cases

- RACF security assessments
- CIS Benchmark validation
- STIG evidence generation
- Internal audit preparation
- Continuous RACF posture monitoring
- Security baseline verification
- Mainframe compliance automation

---

## License

GNU Affero General Public License v3.0 (AGPL-3.0)
