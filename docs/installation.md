# Installation

## Requirements

- Python **3.9 or later**
- A Python virtual environment (recommended)

---

## Install via pip

```bash
pip install mfaudit
```

This installs:

- the `mfaudit` CLI;
- bundled templates;
- required Python dependencies;
- WeasyPrint PDF support.

### Verify installation

```bash
mfaudit --help
```

---

## Output formats

MFAudit supports multiple output formats:

| Format | Output file |
|---|---|
| `PDF` | `report.pdf` |
| `CSV` | `controls_results.csv` |
| `JSON` | `controls_results.json` |

Examples:

```bash
# Default outputs
mfaudit --controls controls.yaml

# JSON only
mfaudit --controls controls.yaml \
         --format JSON

# CSV + JSON + PDF
mfaudit --controls controls.yaml \
         --format CSV,JSON,PDF
```

Default behavior:

```bash
--format CSV,PDF
```

---

## Pure-Python PDF fallback

If WeasyPrint system libraries cannot be installed, use the xhtml2pdf fallback renderer:

```bash
pip install "mfaudit[pdf-xhtml]"
```

MFAudit automatically:

1. tries WeasyPrint first;
2. falls back to xhtml2pdf if installed;
3. continues generating CSV/JSON output even if PDF rendering fails.

---

## System libraries for WeasyPrint

### macOS (Homebrew)

```bash
brew install pango cairo gobject-introspection
```

### Debian / Ubuntu

```bash
sudo apt-get install -y \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libcairo-gobject2 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    shared-mime-info
```

### RHEL / CentOS

```bash
sudo yum install -y \
    pango \
    cairo \
    gdk-pixbuf2 \
    libffi
```

### Windows

Install the GTK3 runtime:

```text
https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases
```

Then add the GTK `bin` directory to `PATH`.

Typical example:

```text
C:\Program Files\GTK3-Runtime Win64\bin
```

Alternative without GTK:

```bash
pip install "mfaudit[pdf-xhtml]"
```

xhtml2pdf requires no GTK libraries.

---

## Get the controls library

The pip package installs the MFAudit engine and CLI.

The CIS/STIG YAML controls library is maintained in the repository.

Clone it once:

```bash
git clone https://github.com/wizardofzos/mfaudit.git
cd mfaudit
```

You can run MFAudit from any location by passing explicit paths:

```bash
mfaudit \
  --controls /path/to/controls.yaml \
  --irrdbu00 /path/to/IRRDBU00 \
  --setropts /path/to/SETROPTS
```

List bundled controls:

```bash
mfaudit --list-controls
```

---

## Installing for development

To work on MFAudit itself:

```bash
git clone https://github.com/wizardofzos/mfaudit.git
cd mfaudit

python3 -m venv .venv

# Linux / macOS
source .venv/bin/activate

# Windows
# .venv\Scripts\activate

pip install -e .
```

### Development with xhtml2pdf fallback

```bash
pip install -e ".[pdf-xhtml]"
```

---

## Development workflow

Run MFAudit directly from the local source tree:

```bash
python3 mfaudit.py --controls controls.yaml
```

Or:

```bash
./mfaudit.py --controls controls.yaml
```

Make the file executable first if needed:

```bash
chmod +x mfaudit.py
```

This bypasses any globally installed version during development.

---

## Verify PDF rendering

Test PDF generation:

```bash
mfaudit \
  --controls controls.yaml \
  --format PDF
```

Expected output:

```text
[+] PDF report written to report.pdf
```

---

## Verify JSON export

Test JSON generation:

```bash
mfaudit \
  --controls controls.yaml \
  --format JSON
```

Expected output:

```text
[+] JSON results written to controls_results.json
```