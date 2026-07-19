# MFAudit

[![PyPI Downloads](https://static.pepy.tech/personalized-badge/mfaudit?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads)](https://pepy.tech/projects/mfaudit)

**Automated RACF security auditing — from raw RACF exports to audit-ready reports in a single command.**

MFAudit reads standard z/OS security exports — IRRDBU00 unloads, SETROPTS
exports, optional DCOLLECT data, and runtime system inventories — and evaluates
them against CIS Benchmark, STIG, and custom RACF security controls.

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

# 2  Run the audit (bundled CIS controls used by default)
mfaudit \
  --irrdbu00 /path/to/IRRDBU00 \
  --setropts /path/to/SETROPTS

# 3  Open the report
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

Generated file:

```text
controls_results.json
```

### Multiple output formats

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

| Source | Contents |
|---|---|
| `--setropts FILE` | IRRXUTIL/REXX `KEY:VALUE` export or raw `SETROPTS LIST` output |
| `--irrdbu00 FILE` | IRRDBU00 RACF database unload |
| `--dcollect FILE` | IDCAMS DCOLLECT output (optional) |
| `--apf-list FILE` | Active APF-authorized data sets |
| `--parmlib-list FILE` | Active PARMLIB concatenation |
| `--proclib-list FILE` | Active STC/TSO PROCLIB data sets |
| `--lpa-list FILE` | Active LPA concatenation |
| `--master-catalog FILE` | Active master catalog data set name(s) |
| `--racf-db-list FILE` | Primary and backup RACF database data sets |
| `--sysprog-list FILE` | Approved system-programmer user or group IDs |
| `--inventory FILE` | YAML file containing any or all of the seven runtime lists above |

Each individual runtime-list file contains one data set name or ID per line.
Blank lines and lines beginning with `#` or `*` are ignored. Entries are
normalized to uppercase and deduplicated.

The same information can be supplied in one inventory file:

```yaml
apf:
  - SYS1.LINKLIB
  - SYS1.SVCLIB
parmlib:
  - SYS1.PARMLIB
proclib:
  - SYS1.PROCLIB
lpa:
  - SYS1.LPALIB
master_catalog:
  - SYS1.MASTER.CATALOG
racf_db:
  - SYS1.RACF.PRIMARY
  - SYS1.RACF.BACKUP
sysprog:
  - SYSPROG
  - RACFADM
```

```bash
mfaudit --irrdbu00 IRRDBU00 \
        --setropts SETROPTS \
        --inventory inventory.yaml
```

An individual flag overrides the corresponding inventory section. For
example, `--apf-list current-apf.txt --inventory inventory.yaml` uses
`current-apf.txt` for APF and the YAML file for the other lists.

These inputs describe the active runtime configuration; MFAudit combines them
with RACF profiles and access lists from IRRDBU00. A control that declares an
optional source but does not receive it is marked `SKIP`. The `sysprog` list
also lets writer-review controls treat WRITE access held only by approved IDs
as resolved instead of requiring review.

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
mfaudit --template terminal
```

List available templates:

```bash
mfaudit --list-templates
```

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
