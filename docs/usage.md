# Usage reference

---

## `mfaudit` — main audit runner

```bash
mfaudit [options]
```

### Optional arguments

| Argument | Default | Description |
|---|---|---|
| `--controls FILE [FILE …]` | bundled controls | One or more controls YAML files. Controls from all files are merged before execution. Defaults to all YAML files bundled with the package (`mfaudit/controls/`). Run `--list-controls` to see the bundled paths. |
| `--out DIR` | current directory | Output directory. Created automatically if it does not exist. |
| `--irrdbu00 PATH` | `./IRRDBU00` | Path to the IRRDBU00 database unload. |
| `--setropts PATH` | `./SETROPTS` | Path to SETROPTS data — either the REXX-produced `KEY:VALUE` export or raw `SETROPTS LIST` console/spool output (the format is auto-detected). |
| `--dcollect PATH` | *(not loaded)* | Path to a DCOLLECT output file. Required only by controls that use it. |
| `--apf-list PATH` | *(not loaded)* | Active APF-authorized data sets, one per line. |
| `--parmlib-list PATH` | *(not loaded)* | Active PARMLIB concatenation, one data set per line. |
| `--proclib-list PATH` | *(not loaded)* | Active STC/TSO PROCLIB data sets, one per line. |
| `--lpa-list PATH` | *(not loaded)* | Active LPA concatenation, one data set per line. |
| `--master-catalog PATH` | *(not loaded)* | Active master catalog data set name(s), one per line. |
| `--racf-db-list PATH` | *(not loaded)* | Primary and backup RACF database data sets, one per line. |
| `--sysprog-list PATH` | *(not loaded)* | Approved system-programmer user/group IDs, one per line. Writer-review controls treat WRITE access held only by these IDs as resolved. |
| `--inventory PATH` | *(not loaded)* | YAML mapping containing any runtime lists. Individual list flags override matching inventory sections. |
| `--system-name NAME` | `UNKNOWN` | Mainframe system identifier shown in the report header. |
| `--report-date DATE` | Today's date | ISO-format date (`YYYY-MM-DD`) shown in the report header. |
| `--template NAME\|FILE` | `default` | Bundled template short name (e.g. `terminal`) or path to a `.html.j2` file. |
| `--format CSV,PDF,JSON` | `CSV,PDF` | Comma-separated output formats to generate. Supported values: `CSV`, `PDF`, `JSON`. |
| `--list-templates` | — | Print available bundled template names and exit. |
| `--anonymize` | off | Replace all RACF user, group, and profile names with stable labels before writing output. Useful when sharing reports externally. |
| `--list-controls` | — | Print paths of bundled controls YAML files and exit. |

### Runtime-list and inventory format

The APF, PARMLIB, PROCLIB, LPA, master-catalog, and RACF-database files contain
one data set name per line. The system-programmer file contains one RACF user
or group ID per line. Blank lines and lines beginning with `#` or `*` (after
optional whitespace) are ignored. Values are normalized to uppercase,
deduplicated, and sorted.

`--inventory` accepts the same data as YAML:

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

The supported section names are exactly `apf`, `parmlib`, `proclib`, `lpa`,
`master_catalog`, `racf_db`, and `sysprog`. The root must be a YAML mapping and
section values must be lists. Unknown sections produce a warning and are
ignored.

Precedence is per section. An explicitly supplied flag replaces only its
corresponding inventory section:

```bash
mfaudit --inventory inventory.yaml --apf-list current-apf.txt
```

This uses `current-apf.txt` for APF and `inventory.yaml` for all other
available sections. Controls whose declared input is unavailable are `SKIP`.

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
         --dcollect /exports/DCOLLECT \
         --inventory /exports/inventory.yaml \
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
