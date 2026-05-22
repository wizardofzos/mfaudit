# Report output

`mfaudit` writes output files after every run. By default all outputs are written to the current directory; use `--out DIR` to choose a different location.

The generated outputs depend on the selected `--format` value.

---

## PDF report — `report.pdf`

Generated when `PDF` is included in `--format`.

```bash
mfaudit --controls controls.yaml --format PDF
```

The primary human-readable output. Open it in any PDF viewer.

### Structure

**Cover page**

- System name and report date
- Summary counts: total controls, PASS / FAIL / REVIEW / SKIP / ERROR
- Overall compliance score

**Per-benchmark sections**

Controls are grouped by source:

- CIS IBM z/OS Benchmark
- CIS IBM Db2 13 Benchmark
- CIS IBM CICS Benchmark
- Custom controls

Each section lists controls in order with:

| Column | Content |
|---|---|
| ID | Control identifier |
| Title | Short description |
| Severity | `HIGH` / `MEDIUM` / `LOW` badge |
| Status | `PASS` / `FAIL` / `REVIEW` / `SKIP` / `ERROR` badge |
| Detail | One-line summary |

**Finding detail**

FAIL and REVIEW controls expand to show the raw finding rows — the actual RACF records that triggered the verdict. Column names are the native mfpandas DataFrame column names.

### PDF library installation

WeasyPrint is installed automatically with:

```bash
pip install mfaudit
```

It is the preferred PDF engine and requires a small set of native system libraries.

=== "macOS"

    ```bash
    brew install pango cairo gobject-introspection
    ```

=== "Debian / Ubuntu"

    ```bash
    sudo apt-get install -y \
        libpango-1.0-0 libpangoft2-1.0-0 libpangocairo-1.0-0 \
        libcairo2 libffi-dev shared-mime-info
    ```

=== "Windows"

    Install the GTK3 runtime:

    https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases

    Then add the GTK `bin` directory to `PATH`.

    Or skip WeasyPrint and use xhtml2pdf instead:

    ```bash
    pip install "mfaudit[pdf-xhtml]"
    ```

If WeasyPrint is unavailable, MFAudit automatically falls back to xhtml2pdf (when installed).

---

## CSV export — `controls_results.csv`

Generated when `CSV` is included in `--format`.

```bash
mfaudit --controls controls.yaml --format CSV
```

One row per control. Useful for spreadsheets, dashboards, SIEM ingestion, ticketing systems, or audit evidence tracking.

| Column | Content |
|---|---|
| `control_id` | Stable control identifier |
| `title` | Control title |
| `cis_section` | CIS section identifier |
| `severity` | `HIGH` / `MEDIUM` / `LOW` |
| `status` | `PASS` / `FAIL` / `REVIEW` / `SKIP` / `ERROR` |
| `detail` | One-line verdict summary |
| `data_sources` | Comma-separated list of required sources |
| `stig_rule_id` | Linked STIG rule identifier if present |

---

## JSON export — `controls_results.json`

Generated when `JSON` is included in `--format`.

```bash
mfaudit --controls controls.yaml --format JSON
```

The JSON export contains the same control-level data as the CSV output, but structured as JSON objects for easier automation and ingestion into APIs, Splunk, Elastic, SIEM pipelines, dashboards, or custom tooling.

Example structure:

```json
[
  {
    "control_id": "1.1.1",
    "title": "Verify PASSWORD interval",
    "cis_section": "1.1",
    "severity": "HIGH",
    "status": "PASS",
    "detail": "PASSWORD interval compliant",
    "data_sources": [
      "setropts"
    ],
    "stig_rule_id": "RACF-0001"
  }
]
```

---

## Multiple output formats

Formats can be combined using comma-separated values:

```bash
mfaudit --controls controls.yaml --format CSV,JSON,PDF
```

Supported values:

| Format | Output |
|---|---|
| `PDF` | `report.pdf` |
| `CSV` | `controls_results.csv` |
| `JSON` | `controls_results.json` |

Default behavior:

```bash
--format CSV,PDF
```

---

## Anonymized reports

Pass `--anonymize` to replace all RACF user IDs, group names, and profile names with stable pseudonymous labels (`USR-0001`, `GRP-0042`, etc.) before writing output.

```bash
mfaudit --controls controls.yaml \
         --format CSV,JSON,PDF \
         --anonymize \
         --out out/
```

The mapping is deterministic within a single run — the same identifier always resolves to the same anonymized label, keeping findings readable while preventing disclosure of internal naming conventions.

Useful when sharing reports with:

- external auditors;
- vendors;
- penetration testers;
- compliance assessors;
- third parties.

---

## Customizing the report

### Bundled templates

Two templates ship with MFAudit:

| Template | Style |
|---|---|
| `templates/default-report.html.j2` | Light corporate theme — default |
| `templates/terminal-report.html.j2` | Dark phosphor-green 3270-style terminal theme |

Use the terminal theme:

```bash
mfaudit --controls controls.yaml --template terminal
```

List available templates:

```bash
mfaudit --list-templates
```

Or use a custom local template:

```bash
mfaudit --controls controls.yaml \
         --template /path/to/my-report.html.j2
```

### Writing your own template

Templates are standard Jinja2 HTML files rendered to HTML and then converted to PDF.

Inline CSS is recommended (`<style>` inside `<head>`) to avoid external stylesheet dependencies.

Available template variables:

| Variable | Type | Content |
|---|---|---|
| `system_name` | str | Value of `--system-name` |
| `report_date` | str | Value of `--report-date` |
| `generated_at` | str | Runtime timestamp |
| `controls_file` | str | Controls file(s) used |
| `total` | int | Total control count |
| `passed` / `failed` / `review` / `skipped` / `errors` | int | Per-status counts |
| `score_pct` | int | `passed / (total - skipped) × 100` |
| `results` | list | One dict per control |
| `sections` | dict | Results grouped by section/category |
| `anonymized` | bool | True if `--anonymize` was used |
| `STATUS_PASS` … `STATUS_ERROR` | str | Status string constants |

Each entry in `results` contains:

- `control_id`
- `title`
- `cis_section`
- `cis_level`
- `custom_benchmark`
- `custom_category`
- `custom_reference`
- `severity`
- `requirement`
- `remediation`
- `data_sources_needed`
- `status`
- `detail`
- `findings`

Start from one of the bundled templates and customize as needed.