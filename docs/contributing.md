# Contributing

MFAudit is open source under the AGPL v3 license and contributions are welcome.

The areas where help is currently most valuable:

- STIG controls;
- report templates;
- additional benchmark mappings;
- documentation improvements;
- bug fixes and engine enhancements.

---

## Where to start

| Area | What's needed | Skills |
|---|---|---|
| STIG controls | DISA STIG rules translated into MFAudit YAML controls | RACF + YAML |
| Report templates | Additional PDF/Jinja2 themes | HTML + CSS |
| JSON / SIEM integrations | Splunk, Elastic, API workflows | Python |
| Bug fixes / improvements | Engine improvements and issue fixes | Python |
| Documentation | Examples, corrections, explanations | Technical writing |

---

## STIG controls

The CIS z/OS Benchmark provides a strong baseline, but many organizations also require compliance with:

- DISA STIG;
- internal hardening standards;
- organization-specific RACF policies.

A community-maintained `stig_controls.yaml` would be highly valuable.

DISA STIG reference:

```text
https://public.cyber.mil/stigs/
```

### Example STIG control

```yaml
controls:
  - control_id: STIG-RACF-001
    title: "RACF must protect SMF data sets"

    severity: high

    custom:
      benchmark: "DISA STIG z/OS RACF V8R12"
      category: "Audit and Accountability"
      reference: "RACF-001"

    data_sources_needed:
      - irrdbu00

    implementation:
      engine: pandas_query

      dataset: irrdbu00.datasets

      select_columns:
        - DSBD_NAME
        - DSBD_UACC

      filter: >
        DSBD_NAME.str.startswith('SYS1.MAN')
        and DSBD_UACC != 'NONE'

      assertion:
        type: no_rows
        pass_message: "SMF datasets are protected"
        fail_message: "{n} SMF dataset profile(s) with UACC other than NONE"

    remediation: >
      ALTDSD 'SYS1.MAN*' UACC(NONE)
```

See:

- `docs/authoring/index.md`
- `examples/easy.md`

for the complete schema and common implementation patterns.

---

## Custom controls

MFAudit supports organization-specific controls alongside CIS/STIG controls.

Examples:

- APF authorization exposure;
- SURROGAT misuse detection;
- OPERCMDS hardening;
- JES2/JES3 access validation;
- sensitive dataset protection;
- USS hardening;
- started task validation;
- naming standard enforcement;
- password/passphrase policy checks;
- custom compliance frameworks.

Custom controls use the same YAML structure and execution engine.

---

## JSON and SIEM integrations

MFAudit supports native JSON export:

```bash
mfaudit --controls controls.yaml \
         --format JSON
```

This makes it easier to integrate with:

- Splunk;
- Elastic;
- Sentinel;
- dashboards;
- CI/CD pipelines;
- evidence collection workflows;
- compliance automation tooling.

Example combined outputs:

```bash
mfaudit --controls controls.yaml \
         --format CSV,JSON,PDF
```

---

## Report templates

MFAudit ships with two bundled templates:

| Template | Style |
|---|---|
| `default` | Light corporate report |
| `terminal` | Green phosphor 3270-style terminal theme |

Additional themes are encouraged.

Ideas:

- accessibility-focused high contrast;
- black-and-white print mode;
- executive summary dashboards;
- branded corporate reports;
- dark mode themes;
- minimal audit evidence exports.

### Template requirements

- Single `.html.j2` Jinja2 template
- Inline CSS only
- No external dependencies
- Must render correctly via WeasyPrint
- Should support PDF printing cleanly

Use existing template variables already exposed by MFAudit.

See:

```text
mfaudit/templates/
```

for examples.

Templates become immediately usable:

```bash
mfaudit --controls controls.yaml \
         --template my-template
```

List templates:

```bash
mfaudit --list-templates
```

---

## Development setup

Clone the repository:

```bash
git clone https://github.com/wizardofzos/mfaudit.git
cd mfaudit
```

Create a virtual environment:

```bash
python3 -m venv .venv
```

Activate it:

### Linux / macOS

```bash
source .venv/bin/activate
```

### Windows

```powershell
.venv\Scripts\activate
```

Install MFAudit in editable mode:

```bash
pip install -e .
```

Optional xhtml2pdf fallback:

```bash
pip install -e ".[pdf-xhtml]"
```

Install documentation dependencies:

```bash
pip install -e ".[docs]"
```

---

## Running locally

Run directly from the source tree:

```bash
python3 mfaudit.py --controls controls.yaml
```

Or:

```bash
./mfaudit.py --controls controls.yaml
```

Example with all outputs:

```bash
python3 mfaudit.py \
  --controls controls.yaml \
  --format CSV,JSON,PDF
```

---

## Documentation development

Serve the documentation locally:

```bash
mkdocs serve
```

Default local URL:

```text
http://127.0.0.1:8000
```

---

## Submitting a contribution

1. Fork the repository
2. Create a branch

```bash
git checkout -b my-contribution
```

3. Make your changes
4. Open a pull request against `main`

Please include:

- what changed;
- why the change was made;
- example usage if applicable;
- related issue references if available.

For STIG controls:

- include the original STIG rule ID;
- preserve traceability back to the source requirement.

---

## Coding guidelines

Preferred characteristics:

- deterministic output;
- audit-friendly logic;
- readable findings;
- explicit remediation guidance;
- stable schemas;
- reproducible execution.

Avoid:

- hidden assumptions;
- nondeterministic logic;
- implicit environment dependencies.

---

## License

By contributing, you agree that your contribution is released under the same:

```text
GNU Affero General Public License v3.0 (AGPL-3.0)
```

as the rest of the MFAudit project.