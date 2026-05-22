# Quick start

This page walks you through your first MFAudit run — from collecting data on the mainframe to opening the finished report.

---

## Step 1 — Collect data on z/OS

You need two files from the mainframe:

| File | What it contains |
|---|---|
| `IRRDBU00` | Full RACF database unload (users, groups, profiles, access lists) |
| `SETROPTS` | RACF global option export (password rules, active classes, flags) |

### IRRDBU00 unload

Submit the IRRDBU00 batch utility.

Minimal JCL example:

```jcl
//RACFUNLD JOB  CLASS=A,MSGCLASS=X
//STEP1    EXEC PGM=IRRDBU00,PARM='NOLOCKINPUT'
//SYSPRINT DD   SYSOUT=*
//INDD1    DD   DSN=SYS1.RACF,DISP=SHR
//OUTDD1   DD   DSN=&&UNLOAD,DISP=(NEW,PASS),
//             UNIT=SYSDA,SPACE=(CYL,(50,10))
//SYSIN    DD   DUMMY
```

Copy the output dataset to your workstation as a binary file.

### SETROPTS REXX export

MFAudit requires a REXX-produced SETROPTS export — not raw `SETROPTS LIST` console output.

See the mfpandas SETROPTS documentation:

https://mfpandas.readthedocs.io/en/latest/setropts.html

The exec writes one `KEY:VALUE` line per setting.

Copy `SETROPTS` to your workstation as a text file.

---

## Step 2 — Install MFAudit

Install the package:

```bash
pip install mfaudit
```

WeasyPrint is installed automatically and used for PDF generation.

See the installation guide for required native libraries on Linux/macOS/Windows.

Clone the repository to get the bundled controls library and templates:

```bash
git clone https://github.com/wizardofzos/mfaudit.git
cd mfaudit
```

---

## Step 3 — Run the audit

Place `IRRDBU00` and `SETROPTS` in the project root directory, or pass explicit paths.

### Minimal run

Outputs are written to the current directory.

```bash
mfaudit --controls controls.yaml
```

Default outputs:

- `report.pdf`
- `controls_results.csv`

### JSON output

```bash
mfaudit --controls controls.yaml \
         --format JSON
```

Output:

- `controls_results.json`

### Multiple output formats

```bash
mfaudit --controls controls.yaml \
         --format CSV,JSON,PDF
```

Outputs:

- `report.pdf`
- `controls_results.csv`
- `controls_results.json`

### Full example

```bash
mfaudit --irrdbu00 /data/IRRDBU00 \
         --setropts  /data/SETROPTS \
         --controls  controls.yaml \
         --system-name SYSA \
         --report-date 2026-05-17 \
         --format CSV,JSON,PDF \
         --out out/
```

### Anonymized output

Replace RACF user IDs, groups, and profile names with stable labels before writing output:

```bash
mfaudit --controls controls.yaml \
         --format CSV,JSON,PDF \
         --anonymize \
         --out out/
```

Example anonymized identifiers:

- `USR-0001`
- `GRP-0007`
- `PRF-0042`

Useful when sharing reports externally.

---

## Step 4 — Open the report

### macOS

```bash
open out/report.pdf
```

### Linux

```bash
xdg-open out/report.pdf
```

### Windows

```powershell
start out\report.pdf
```

CSV results:

```text
out/controls_results.csv
```

JSON results:

```text
out/controls_results.json
```

---

## What you see on the console

```text
[+] Loaded 46 control(s) from controls.yaml
[+] Total: 46 control(s)

[+] Loading SETROPTS from SETROPTS
[+] Loading IRRDBU00 from IRRDBU00 (threaded parse) ...

[CIS-1.1.1] Ensure PASSWORD(INTERVAL) is set to no longer than 90 days ... ✓ PASS
[CIS-1.1.2] Ensure PASSWORD(HISTORY) is set to at least 4 ............... ✓ PASS
[CIS-1.2.5] Ensure started tasks defined with TRUSTED attribute ......... ? REVIEW

────────────────────────────────────────────────────────────
Results: 40 PASS  |  3 FAIL  |  1 REVIEW  |  2 SKIP
Score:   40/44 = 90%
────────────────────────────────────────────────────────────

[+] PDF report written to out/report.pdf
[+] CSV results written to out/controls_results.csv
[+] JSON results written to out/controls_results.json

Done.
```

Controls that cannot run because a required data source was not supplied are automatically marked as `SKIP`.

Skipped controls do not count as failures.