# MFAudit

**Automated RACF security auditing — from raw RACF exports to audit-ready reports in a single command.**

MFAudit reads standard z/OS security exports — IRRDBU00 unloads and SETROPTS REXX exports — and evaluates them against CIS Benchmark, STIG, and custom RACF security controls.

The result:

- styled PDF reports;
- CSV exports;
- JSON exports;
- deterministic PASS / FAIL / REVIEW verdicts;
- optional anonymized output for external sharing.

**[Full documentation → mfaudit.readthedocs.io](https://mfaudit.readthedocs.io/)**

---

## What you get

| | |
|---|---|
| **46+ CIS controls** | Password policy, class activation, STARTED tasks, USS, Db2, CICS |
| **Custom controls** | Write organization-specific RACF checks in YAML |
| **PDF reports** | Human-readable audit reports with findings and summaries |
| **CSV exports** | Spreadsheet, SIEM, and dashboard integration |
| **JSON exports** | Splunk, Elastic, APIs, and automation workflows |
| **Anonymized reports** | Replace RACF identifiers with stable pseudonymous labels |

---

## Quick start

```bash
# 1  Install MFAudit
pip install mfaudit

# 2  Clone the repository to get the controls library
git clone https://github.com/wizardofzos/mfaudit.git
cd mfaudit

# 3  Run the audit
mfaudit \
  --irrdbu00 /path/to/IRRDBU00 \
  --setropts /path/to/SETROPTS \
  --controls controls.yaml

# 4  Open the report
open report.pdf             # macOS
xdg-open report.pdf         # Linux
start report.pdf            # Windows
```

Default behavior:

```text
--format CSV,PDF
```

Controls requiring unavailable data sources are automatically marked as `SKIP`.

---

## Output formats

### Default outputs

```bash
mfaudit --controls controls.yaml
```

Generated files:

```text
report.pdf
controls_results.csv
```

### JSON output

```bash
mfaudit --controls controls.yaml \
         --format JSON
```

Generated file:

```text
controls_results.json
```

### Multiple output formats

```bash
mfaudit --controls controls.yaml \
         --format CSV,JSON,PDF
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

## Repository layout

```text
controls.yaml               CIS Benchmark controls
example_controls.yaml       Example custom controls
mfaudit/                    Python package and CLI
templates/                  Bundled report templates
docs/                       MkDocs / ReadTheDocs documentation
```

---

## Writing your own controls

Controls are YAML-based.

Each control explicitly defines:

- the required data source;
- the mfpandas DataFrame;
- the logic engine;
- the assertion logic;
- remediation guidance.

Example:

```yaml
controls:
  - control_id: CUSTOM-NO-DUAL-PRIVS

    title: "No active user may hold both SPECIAL and OPERATIONS"

    severity: high

    custom:
      benchmark: "Internal policy"
      category: "Privileged access"

    data_sources_needed:
      - irrdbu00

    implementation:
      engine: python

      dataset: irrdbu00.users

      select_columns:
        - USBD_NAME
        - USBD_SPECIAL
        - USBD_OPER

      logic: |
        hits = df[
            (df['USBD_SPECIAL'] == 'YES') &
            (df['USBD_OPER'] == 'YES') &
            (df['USBD_REVOKE'] != 'YES')
        ]

        status = 'FAIL' if not hits.empty else 'PASS'

        detail = f"{len(hits)} user(s) hold both SPECIAL and OPERATIONS"

        findings = hits.to_dict('records')

    remediation: >
      ALTUSER <userid> NOSPECIAL
      or
      ALTUSER <userid> NOOPER
```

### Available engines

| Engine | Use case |
|---|---|
| `pandas_query` | Simple DataFrame filtering and assertions |
| `python` | Multi-DataFrame logic, branching, advanced analysis |

See:

**[Authoring controls →](https://mfaudit.readthedocs.io/authoring/)**

for the complete schema and engine reference.

---

## Data sources

| Source | mfpandas class | Collection method |
|---|---|---|
| `--setropts` | `SETROPTS` | IRRXUTIL/REXX export (`KEY:VALUE`) |
| `--irrdbu00` | `IRRDBU00` | IRRDBU00 RACF unload |
| `--dcollect` | `DCOLLECT` | IDCAMS DCOLLECT output (optional) |

See:

**[Quick start guide →](https://mfaudit.readthedocs.io/quickstart/)**

for detailed collection instructions.

---

## Templates

Bundled templates:

| Template | Style |
|---|---|
| `default` | Light corporate report |
| `terminal` | Green phosphor 3270-style terminal theme |

Example:

```bash
mfaudit --controls controls.yaml \
         --template terminal
```

List available templates:

```bash
mfaudit --list-templates
```

---

## Anonymized reporting

Generate reports safe for external sharing:

```bash
mfaudit --controls controls.yaml \
         --format CSV,JSON,PDF \
         --anonymize
```

Example anonymized identifiers:

```text
USR-0001
GRP-0042
PRF-0017
```

Mappings remain stable during a single execution run so findings remain readable and correlatable.

---

## Requirements

- Python 3.9 or later
- `pip install mfaudit`
- Optional:
  - `pip install "mfaudit[pdf-xhtml]"`

WeasyPrint is the preferred PDF renderer.

If unavailable, MFAudit automatically falls back to xhtml2pdf when installed.

CSV and JSON output remain available even if PDF rendering fails.

---

## Use cases

- RACF security assessments
- CIS Benchmark validation
- STIG evidence generation
- Internal audit preparation
- Mainframe compliance automation
- Continuous RACF posture monitoring
- Security baseline verification
- SIEM evidence export
- Splunk/Elastic integrations

---

## Disclaimer

All findings must be reviewed and validated by qualified RACF security personnel before remediation.

`REVIEW` status findings require human assessment and cannot be automatically classified as compliant or non-compliant.