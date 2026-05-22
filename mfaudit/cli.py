#!/usr/bin/env python3
# MFAudit — RACF Security Audit Report Generator (CIS Benchmarks).
# Copyright (C) 2026  Wizard of z/OS <henri@mainframesociety.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Affero General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
MFAudit – RACF Security Audit Report Generator
CIS z/OS 2.5.0 Benchmark, Phase 1

Usage:
  mfaudit \
    --controls  controls.yaml \
    [--out       out/]              # default: current directory
    [--setropts  SETROPTS]          # default: ./SETROPTS
    [--irrdbu00  IRRDBU00]          # default: ./IRRDBU00
    [--dcollect  path/to/dcollect]  # optional, no default
    [--system-name SYSPLEX1] \
    [--report-date 2026-04-16] \
    [--template    path/to/default-report.html.j2] \
    [--anonymize]

Defaults:
  --setropts defaults to the filename "SETROPTS" in the current directory.
  --irrdbu00 defaults to the filename "IRRDBU00" in the current directory.
  If either default file is absent the source is treated as not provided and
  controls that require it are marked SKIP. If you pass an explicit path that
  does not exist the tool exits with an error.

Flags:
  --anonymize   Replace user IDs, group names, and profile names in findings
                with stable opaque labels (USR-NNNN / GRP-NNNN / PRF-NNNN).
                Permit auth IDs resolve to the same label as their user/group
                counterpart. Pass/Fail results and counts are not affected.
                Use this to produce a report safe for external sharing.

Outputs:
  --format PDF   -> <out>/report.pdf
  --format CSV   -> <out>/controls_results.csv
  --format JSON  -> <out>/controls_results.json

Format examples:
  --format CSV
  --format PDF
  --format JSON
  --format CSV,JSON,PDF
"""

import argparse
import csv
import json
import os
import platform
import sys
import time
import traceback
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import yaml
from jinja2 import Environment, FileSystemLoader

# ── macOS: make WeasyPrint find Homebrew's Pango/GObject/Cairo libs ──────────
# WeasyPrint uses cffi to dlopen these at import time. On Apple Silicon and
# Intel Macs the dylibs live under /opt/homebrew/lib or /usr/local/lib but
# are NOT in the default dyld search path for venv-spawned processes.
if platform.system() == "Darwin":
    _brew_lib = ""
    for _candidate in ("/opt/homebrew/lib", "/usr/local/lib"):
        if os.path.exists(os.path.join(_candidate, "libgobject-2.0.dylib")):
            _brew_lib = _candidate
            break
    if _brew_lib:
        _existing = os.environ.get("DYLD_LIBRARY_PATH", "")
        if _brew_lib not in _existing:
            os.environ["DYLD_LIBRARY_PATH"] = (
                f"{_brew_lib}:{_existing}" if _existing else _brew_lib
            )
        # Re-exec so the new DYLD_LIBRARY_PATH takes effect before cffi loads
        if not os.environ.get("_MFAUDIT_REEXEC"):
            os.environ["_MFAUDIT_REEXEC"] = "1"
            os.execv(sys.executable, [sys.executable] + sys.argv)


# ──────────────────────────────────────────────────────────────────────────────
# Argument parsing
# ──────────────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(
        description="MFAudit – RACF CIS Benchmark Audit Report Generator"
    )
    p.add_argument("--setropts",     required=False, metavar="FILE", default="SETROPTS",
                   help="REXX-produced SETROPTS export (KEY:VALUE lines) [default: ./SETROPTS]")
    p.add_argument("--irrdbu00",     required=False, metavar="FILE", default="IRRDBU00",
                   help="IRRDBU00 unload file [default: ./IRRDBU00]")
    p.add_argument("--dcollect",     required=False, metavar="FILE", default=None,
                   help="DCOLLECT unload file (optional)")
    p.add_argument("--controls",     required=False, metavar="FILE", nargs="+",
                   help="Controls definition file(s); repeat or space-separate to merge multiple YAML files. "
                        "Run --list-controls to see bundled file paths.")
    p.add_argument("--list-controls", action="store_true",
                   help="Print paths of the bundled controls YAML files and exit.")
    p.add_argument("--out",          required=False, metavar="DIR", default=".",
                   help="Output directory for report files (default: current directory)")
    p.add_argument("--system-name",  default="UNKNOWN", metavar="NAME",
                   help="System or sysplex name (cosmetic)")
    p.add_argument("--report-date",  default=None,   metavar="YYYY-MM-DD",
                   help="Report date (default: today)")
    p.add_argument("--template",     required=False, metavar="NAME|FILE", default=None,
                   help="Report template: a bundled short name (e.g. 'terminal') or a path to a .html.j2 file. "
                        "Run --list-templates to see available names.")
    p.add_argument("--list-templates", action="store_true",
                   help="Print available bundled template names and exit.")
    p.add_argument("--anonymize", action="store_true",
                   help="Mask user IDs, group names, and profile names in findings "
                        "so the report can be shared externally without exposing "
                        "account names. Pass/Fail results and counts are unchanged.")

    p.add_argument("--format", required=False, default="CSV,PDF",
                   metavar="CSV,PDF,JSON",
                   help="Output format(s), comma separated: CSV, PDF, JSON")
    return p.parse_args()


# ──────────────────────────────────────────────────────────────────────────────
# Anonymization
# ──────────────────────────────────────────────────────────────────────────────

# Columns whose values are definitively a user ID, group name, or resource
# profile name. These are registered in the shared identity map on the first
# pass so that auth-ID columns can resolve to the same label.
_ANON_USER_COLS = {
    "USBD_NAME", "USOMVS_NAME",
    "USCON_NAME",
    "GRST_USER_ID",
}
_ANON_GROUP_COLS = {
    "GPBD_NAME", "GPOMVS_NAME",
    "USCON_GRP_ID", "GRST_GROUP_ID",
    "USBD_DEFGRP_ID",
}
_ANON_PROFILE_COLS = {
    "GRBD_NAME", "GRST_NAME",
    "DSBD_NAME",
    "DSACC_NAME", "GRACC_NAME",
    "GRMEM_NAME", "GRMEM_MEMBER",
}
# Auth-ID columns: value can be a user ID OR a group name.
# Resolved via the shared map on the second pass — no separate namespace.
_ANON_AUTHID_COLS = {
    "DSACC_AUTH_ID", "GRACC_AUTH_ID",
    "USCON_OWNER_ID", "GPBD_OWNER_ID", "DSBD_OWNER_ID",
    "GRBD_OWNER_ID",  "GRST_OWNER_ID",
}

# All typed identifier columns combined — used during first-pass registration.
_ALL_TYPED_COLS = _ANON_USER_COLS | _ANON_GROUP_COLS | _ANON_PROFILE_COLS


class _AnonMap:
    """
    Single shared identity map for the whole report run.

    All user IDs, group names, profile names, and auth IDs live in ONE dict.
    The prefix (USR / GRP / PRF) is fixed at first registration based on
    which column type first introduced the value.

    This means:
      - SYSADM1 seen as USBD_NAME   → registered as USR-0001
      - SYSADM1 seen as DSACC_AUTH_ID later → looks up map → returns USR-0001
      - SYS1    seen as GPBD_NAME    → registered as GRP-0001
      - SYS1    seen as DSACC_AUTH_ID later → returns GRP-0001
    """

    def __init__(self):
        self._map: dict[str, str] = {}   # upper(value) → label
        self._user_ctr    = 0
        self._group_ctr   = 0
        self._profile_ctr = 0
        self._unknown_ctr = 0            # fallback for auth IDs not pre-registered

    def _key(self, value: str) -> str:
        return str(value).strip().upper()

    def _register(self, value: str, prefix: str, counter_attr: str) -> str:
        """Register a value with a given prefix if not already known."""
        if not value or not value.strip():
            return value
        k = self._key(value)
        if k not in self._map:
            setattr(self, counter_attr, getattr(self, counter_attr) + 1)
            self._map[k] = f"{prefix}-{getattr(self, counter_attr):04d}"
        return self._map[k]

    def _resolve(self, value: str, irrdbu00=None) -> str:
        """
        Return the label for value.

        Order of precedence:
          1. Already in map from a previous registration → return it.
          2. irrdbu00 provided → look up the full users/groups DataFrames
             to determine the right prefix, register, and return.
          3. Neither → UNK- fallback (should be extremely rare).
        """
        if not value or not value.strip():
            return value
        k = self._key(value)
        if k in self._map:
            return self._map[k]

        # Try to classify via the full IRRDBU00 DataFrames
        if irrdbu00 is not None:
            try:
                users_df = irrdbu00.users
                if not users_df.empty and k in users_df["USBD_NAME"].str.upper().values:
                    return self._register(value, "USR", "_user_ctr")
            except Exception:
                pass
            try:
                groups_df = irrdbu00.groups
                if not groups_df.empty and k in groups_df["GPBD_NAME"].str.upper().values:
                    return self._register(value, "GRP", "_group_ctr")
            except Exception:
                pass

        # Genuine fallback — auth ID not found anywhere in IRRDBU00
        self._unknown_ctr += 1
        self._map[k] = f"UNK-{self._unknown_ctr:04d}"
        return self._map[k]

    def register_user(self, v: str)    -> str: return self._register(v, "USR", "_user_ctr")
    def register_group(self, v: str)   -> str: return self._register(v, "GRP", "_group_ctr")
    def register_profile(self, v: str) -> str: return self._register(v, "PRF", "_profile_ctr")
    def resolve(self, v: str, irrdbu00=None) -> str: return self._resolve(v, irrdbu00)


def anonymize_results(results: list, irrdbu00=None) -> list:
    """
    Two-pass anonymization over all control findings.

    Pass 1 — registration from findings:
        Walk every finding row in every IRRDBU00-sourced control.
        For each typed column (user / group / profile), register the value
        in the shared identity map with its prefix.

    Pass 2 — replacement:
        Walk again and replace every identifier value using the map.
        Auth-ID columns are resolved via the same map — so a permit for
        user SYSADM1 becomes USR-0001 (not a separate label), and a permit
        for group SYS1 becomes GRP-0001.

        For any auth ID not seen in findings, the full irrdbu00.users and
        irrdbu00.groups DataFrames are consulted to assign the right prefix
        before falling back to UNK-.

    SETROPTS and DCOLLECT findings are never touched.
    Status, detail text, and counts are never modified.
    """
    amap = _AnonMap()

    # ── Pass 1: register typed identifiers from findings ─────────────────────
    for result in results:
        if "irrdbu00" not in result.get("data_sources_needed", []):
            continue
        for row in result.get("findings", []):
            for col, val in row.items():
                sval = str(val) if val is not None else ""
                if col in _ANON_USER_COLS:
                    amap.register_user(sval)
                elif col in _ANON_GROUP_COLS:
                    amap.register_group(sval)
                elif col in _ANON_PROFILE_COLS:
                    amap.register_profile(sval)

    # ── Pass 2: replace all identifier values ────────────────────────────────
    for result in results:
        if "irrdbu00" not in result.get("data_sources_needed", []):
            continue
        anon_findings = []
        for row in result.get("findings", []):
            anon_row = {}
            for col, val in row.items():
                sval = str(val) if val is not None else ""
                if col in _ALL_TYPED_COLS or col in _ANON_AUTHID_COLS:
                    anon_row[col] = amap.resolve(sval, irrdbu00=irrdbu00)
                else:
                    anon_row[col] = val   # non-identifier values unchanged
            anon_findings.append(anon_row)
        result["findings"] = anon_findings

    return results


# ──────────────────────────────────────────────────────────────────────────────
# mfpandas loading helpers
# ──────────────────────────────────────────────────────────────────────────────

def load_setropts(path):
    """Load and return a parsed SETROPTS object, or None."""
    if not path:
        return None
    from mfpandas import SETROPTS
    print(f"[+] Loading SETROPTS from {path}")
    s = SETROPTS(setropts=path)
    return s


def load_irrdbu00(path):
    """Load, parse, and return an IRRDBU00 object, or None."""
    if not path:
        return None
    from mfpandas import IRRDBU00
    print(f"[+] Loading IRRDBU00 from {path} (threaded parse) ...")
    r = IRRDBU00(irrdbu00=path)
    r.parse()

    # Phase 1: poll while records are being read (STATE_PARSING = 1)
    # Phase 2: after all lines are read, the thread builds DataFrames —
    #          _state stays PARSING until that finishes, so we show a
    #          separate "building dataframes" message to avoid appearing stuck.
    last_seen = -1
    while r._state < r.STATE_READY:
        st = r.status
        il = st["input-lines"]
        lr = st["lines-read"]
        pct = int((lr / il) * 100) if il > 0 else 0

        if lr != last_seen:
            # Still reading records
            print(f"\r    reading  : {pct:3d}%  ({lr:,} / {il:,} lines)", end="", flush=True)
            last_seen = lr
        else:
            # All lines consumed; thread is now constructing DataFrames
            print(f"\r    building dataframes ...                           ", end="", flush=True)

        time.sleep(0.4)

    st = r.status
    print(f"\r    done     : {st['lines-parsed']:,} records parsed in {st['parse-time']:.1f}s"
          f"  ({st['error-lines']} error line(s))          ")

    if st["status"] == "Error":
        print("[!] IRRDBU00 parse ended with errors – some frames may be empty")
    return r


def load_dcollect(path):
    """Load and return a DCOLLECT object, or None."""
    if not path:
        return None
    from mfpandas import DCOLLECT
    print(f"[+] Loading DCOLLECT from {path}")
    d = DCOLLECT(dcollect=path)
    d.parse()
    while d.status["status"] not in ("Ready", "Error"):
        time.sleep(0.3)
    return d


# ──────────────────────────────────────────────────────────────────────────────
# Control execution engine
# ──────────────────────────────────────────────────────────────────────────────

STATUS_PASS   = "PASS"
STATUS_FAIL   = "FAIL"
STATUS_REVIEW = "REVIEW"
STATUS_SKIP   = "SKIP"
STATUS_ERROR  = "ERROR"


def _get_df(dataset_spec: str, setropts, irrdbu00, dcollect):
    """Resolve a dataset spec string to a DataFrame."""
    spec = dataset_spec.strip()
    if spec == "setropts.fieldInfo":
        return setropts.fieldInfo if setropts else pd.DataFrame()
    if spec == "setropts.classInfo":
        return setropts.classInfo if setropts else pd.DataFrame()
    if spec == "irrdbu00.users":
        return irrdbu00.users if irrdbu00 else pd.DataFrame()
    if spec == "irrdbu00.groups":
        return irrdbu00.groups if irrdbu00 else pd.DataFrame()
    if spec == "irrdbu00.userOMVS":
        return irrdbu00.userOMVS if irrdbu00 else pd.DataFrame()
    if spec == "irrdbu00.groupOMVS":
        return irrdbu00.groupOMVS if irrdbu00 else pd.DataFrame()
    if spec == "irrdbu00.generalSTDATA":
        return irrdbu00.generalSTDATA if irrdbu00 else pd.DataFrame()
    if spec == "irrdbu00.generals":
        return irrdbu00.generals if irrdbu00 else pd.DataFrame()
    if spec == "irrdbu00.datasets":
        return irrdbu00.datasets if irrdbu00 else pd.DataFrame()
    if spec == "irrdbu00.datasetAccess":
        return irrdbu00.datasetAccess if irrdbu00 else pd.DataFrame()
    if spec == "irrdbu00.generalAccess":
        return irrdbu00.generalAccess if irrdbu00 else pd.DataFrame()
    if spec == "dcollect.datasets":
        return dcollect.datasets if dcollect else pd.DataFrame()
    return pd.DataFrame()


def run_pandas_query(control, impl, setropts, irrdbu00, dcollect):
    """Run a simple pandas_query control."""
    df = _get_df(impl["dataset"], setropts, irrdbu00, dcollect)
    if df.empty:
        return STATUS_SKIP, "Data source not available", []

    flt = impl.get("filter", "")
    assertion = impl.get("assertion", {})

    try:
        if flt:
            row = df.query(flt)
        else:
            row = df

        atype = assertion.get("type", "")

        if atype == "scalar_compare":
            if row.empty:
                return STATUS_FAIL, "Setting not found in data", []
            val_raw = row.iloc[0]["Value"]
            try:
                val = int(val_raw)
            except (ValueError, TypeError):
                val = str(val_raw)
            op  = assertion["operator"]
            exp = assertion["expected"]
            ops = {
                "<=": lambda a, b: a <= b,
                ">=": lambda a, b: a >= b,
                ">":  lambda a, b: a > b,
                "<":  lambda a, b: a < b,
                "==": lambda a, b: a == b,
                "!=": lambda a, b: a != b,
            }
            passed = ops[op](val, exp)
            msg_tmpl = assertion["pass_message"] if passed else assertion["fail_message"]
            msg = msg_tmpl.replace("{value}", str(val))
            status = STATUS_PASS if passed else STATUS_FAIL
            findings = row.to_dict("records")
            return status, msg, findings

        if atype == "no_rows":
            count = len(row)
            if count == 0:
                return STATUS_PASS, assertion.get("pass_message", "No violations"), []
            else:
                return STATUS_FAIL, assertion.get("fail_message", f"{count} finding(s)"), row.to_dict("records")

    except Exception as exc:
        return STATUS_ERROR, f"Query error: {exc}", []

    return STATUS_SKIP, "Unhandled assertion type", []


def run_python_control(control, impl, setropts, irrdbu00, dcollect):
    """Execute inline Python logic defined in controls.yaml."""
    dataset_spec = impl.get("dataset", "")
    logic = impl.get("logic", "")

    # Build execution namespace
    ns = {
        "pd": pd,
        "setropts": setropts,
        "irrdbu00": irrdbu00,
        "dcollect": dcollect,
        "status": STATUS_SKIP,
        "detail": "",
        "findings": [],
        "count": 0,
    }

    # Support combined specs like "irrdbu00.userOMVS + irrdbu00.users"
    specs = [s.strip() for s in dataset_spec.split("+")]
    if len(specs) == 1:
        ns["df"] = _get_df(specs[0], setropts, irrdbu00, dcollect)
    else:
        # Provide individual named DataFrames
        for spec in specs:
            parts = spec.split(".")
            if len(parts) == 2:
                src, attr = parts
                if src == "irrdbu00" and attr == "userOMVS":
                    ns["omvs_df"] = _get_df(spec, setropts, irrdbu00, dcollect)
                elif src == "irrdbu00" and attr == "users":
                    ns["users_df"] = _get_df(spec, setropts, irrdbu00, dcollect)
                elif src == "irrdbu00" and attr == "groupOMVS":
                    ns["gomvs_df"] = _get_df(spec, setropts, irrdbu00, dcollect)
                elif src == "irrdbu00" and attr == "generalAccess":
                    ns["access_df"] = _get_df(spec, setropts, irrdbu00, dcollect)
                elif src == "irrdbu00" and attr == "groups":
                    ns["groups_df"] = _get_df(spec, setropts, irrdbu00, dcollect)
                else:
                    ns["df"] = _get_df(spec, setropts, irrdbu00, dcollect)

    # Check if primary df (or combined dfs) are empty
    primary_df = ns.get("df", ns.get("omvs_df", ns.get("access_df", pd.DataFrame())))
    if primary_df is None or (isinstance(primary_df, pd.DataFrame) and primary_df.empty):
        required = impl.get("../data_sources_needed", control.get("data_sources_needed", []))
        if "setropts" in required and setropts is None:
            return STATUS_SKIP, "SETROPTS data not provided", []
        if "irrdbu00" in required and irrdbu00 is None:
            return STATUS_SKIP, "IRRDBU00 data not provided", []

    try:
        exec(logic, ns)
    except Exception as exc:
        return STATUS_ERROR, f"Logic error: {exc}\n{traceback.format_exc()}", []

    return ns.get("status", STATUS_SKIP), ns.get("detail", ""), ns.get("findings", [])


def run_control(control, setropts, irrdbu00, dcollect):
    """Dispatch and execute a single control. Returns (status, detail, findings)."""
    impl = control.get("implementation", {})
    engine = impl.get("engine", "pandas_query")
    needed = control.get("data_sources_needed", [])

    # Check availability
    if "setropts" in needed and setropts is None:
        return STATUS_SKIP, "SETROPTS not provided (use --setropts)", []
    if "irrdbu00" in needed and irrdbu00 is None:
        return STATUS_SKIP, "IRRDBU00 not provided (use --irrdbu00)", []
    if "dcollect" in needed and dcollect is None:
        return STATUS_SKIP, "DCOLLECT not provided (use --dcollect)", []

    if engine == "pandas_query":
        return run_pandas_query(control, impl, setropts, irrdbu00, dcollect)
    elif engine == "python":
        return run_python_control(control, impl, setropts, irrdbu00, dcollect)
    else:
        return STATUS_SKIP, f"Unknown engine: {engine}", []


# ──────────────────────────────────────────────────────────────────────────────
# Report rendering
# ──────────────────────────────────────────────────────────────────────────────

def render_report(results, system_name, report_date, out_dir, controls_path,
                  anonymized=False, template_path=None, output_formats="CSV,PDF"):
    """Render PDF + CSV + JSON from results list."""

    formats = {
        f.strip().upper()
        for f in output_formats.split(",")
        if f.strip()
    }
    if template_path:
        tp = Path(template_path)
        env = Environment(loader=FileSystemLoader(str(tp.parent)), autoescape=False)
        template = env.get_template(tp.name)
    else:
        template_dir = Path(__file__).parent / "templates"
        env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=False)
        template = env.get_template("default-report.html.j2")

    # Summary stats
    total   = len(results)
    passed  = sum(1 for r in results if r["status"] == STATUS_PASS)
    failed  = sum(1 for r in results if r["status"] == STATUS_FAIL)
    review  = sum(1 for r in results if r["status"] == STATUS_REVIEW)
    skipped = sum(1 for r in results if r["status"] == STATUS_SKIP)
    errors  = sum(1 for r in results if r["status"] == STATUS_ERROR)

    score_pct = int((passed / (total - skipped)) * 100) if (total - skipped) > 0 else 0

    # Group by section (CIS section number, or custom category, or "Custom")
    sections = {}
    for r in results:
        sec = r.get("cis_section", "")
        top = sec.split(".")[0] if sec else (r.get("custom_category") or "Custom")
        sections.setdefault(top, []).append(r)

    context = {
        "system_name":   system_name,
        "report_date":   report_date,
        "generated_at":  datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "controls_file": str(controls_path),
        "total":         total,
        "passed":        passed,
        "failed":        failed,
        "review":        review,
        "skipped":       skipped,
        "errors":        errors,
        "score_pct":     score_pct,
        "results":       results,
        "sections":      sections,
        "STATUS_PASS":   STATUS_PASS,
        "STATUS_FAIL":   STATUS_FAIL,
        "STATUS_REVIEW": STATUS_REVIEW,
        "STATUS_SKIP":   STATUS_SKIP,
        "STATUS_ERROR":  STATUS_ERROR,
        "anonymized":    anonymized,
    }

    html = template.render(**context)

    # PDF — try WeasyPrint first, fall back to xhtml2pdf
    if "PDF" in formats:
        pdf_path = Path(out_dir) / "report.pdf"
        css_path = Path(__file__).parent / "assets" / "report.css"
        _pdf_written = False

        try:
            from weasyprint import HTML as WP_HTML
            WP_HTML(string=html).write_pdf(
                str(pdf_path),
                stylesheets=[str(css_path)] if css_path.exists() else []
            )
            print(f"[+] PDF report written to {pdf_path}  (engine: WeasyPrint)")
            _pdf_written = True
        except Exception as wp_exc:
            print(f"[~] WeasyPrint unavailable ({type(wp_exc).__name__}), trying xhtml2pdf ...")

        if not _pdf_written:
            try:
                from xhtml2pdf import pisa
                # Embed CSS inline so xhtml2pdf can find it (it doesn't follow relative links)
                css_inline = ""
                if css_path.exists():
                    css_inline = f"<style>{css_path.read_text(encoding='utf-8')}</style>"
                html_for_xhtml = html.replace(
                    '<link rel="stylesheet" href="../assets/report.css">',
                    css_inline,
                )
                with open(pdf_path, "wb") as pdf_fh:
                    result = pisa.CreatePDF(html_for_xhtml, dest=pdf_fh)
                if result.err:
                    print(f"[!] xhtml2pdf reported errors (PDF may still be usable): {result.err}")
                else:
                    print(f"[+] PDF report written to {pdf_path}  (engine: xhtml2pdf)")
                _pdf_written = True
            except Exception as px_exc:
                print(f"[!] PDF generation failed with both engines.")
                print(f"    WeasyPrint: install system libs — see README for OS-specific steps.")
                print(f"    xhtml2pdf:  {px_exc}")

    # CSV
    if "CSV" in formats:
        csv_path = Path(out_dir) / "controls_results.csv"

        with open(csv_path, "w", newline="", encoding="utf-8") as fh:
            fields = [
                "control_id",
                "title",
                "cis_section",
                "severity",
                "status",
                "detail",
                "data_sources",
                "stig_rule_id",
            ]

            writer = csv.DictWriter(fh, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()

            for r in results:
                writer.writerow({
                    "control_id": r.get("control_id", ""),
                    "title": r.get("title", ""),
                    "cis_section": r.get("cis_section", ""),
                    "severity": r.get("severity", ""),
                    "status": r.get("status", ""),
                    "detail": r.get("detail", ""),
                    "data_sources": ",".join(r.get("data_sources_needed", [])),
                    "stig_rule_id": r.get("stig_rule_id", ""),
                })

        print(f"[+] CSV results written to {csv_path}")

    # JSON
    if "JSON" in formats:
        json_path = Path(out_dir) / "controls_results.json"

        json_results = []

        for r in results:
            json_results.append({
                "control_id": r.get("control_id", ""),
                "title": r.get("title", ""),
                "cis_section": r.get("cis_section", ""),
                "severity": r.get("severity", ""),
                "status": r.get("status", ""),
                "detail": r.get("detail", ""),
                "data_sources": r.get("data_sources_needed", []),
                "stig_rule_id": r.get("stig_rule_id", ""),
            })

        with open(json_path, "w", encoding="utf-8") as fh:
            json.dump(json_results, fh, indent=2)

        print(f"[+] JSON results written to {json_path}")


# ──────────────────────────────────────────────────────────────────────────────
# Main
# ──────────────────────────────────────────────────────────────────────────────

_BUNDLED_CONTROLS  = Path(__file__).parent / "controls"
_BUNDLED_TEMPLATES = Path(__file__).parent / "templates"


def _short_name(path: Path) -> str:
    """Derive the user-facing short name from a template filename.

    terminal-report.html.j2  →  terminal
    default-report.html.j2   →  default
    my-template.html.j2      →  my-template
    """
    stem = path.name
    for suffix in (".html.j2", ".j2"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
    if stem.endswith("-report"):
        stem = stem[: -len("-report")]
    return stem


def _resolve_template(value: str) -> Path:
    """
    Resolve --template to an absolute Path.

    1. If it's an existing file path → use it directly.
    2. Try  <name>-report.html.j2  in the bundled templates dir.
    3. Try  <name>.html.j2         in the bundled templates dir.
    4. Try any bundled template whose short name starts with <value>.
    5. Abort with a clear error.
    """
    p = Path(value)
    if p.exists():
        return p

    candidates = [
        _BUNDLED_TEMPLATES / f"{value}-report.html.j2",
        _BUNDLED_TEMPLATES / f"{value}.html.j2",
    ]
    for c in candidates:
        if c.exists():
            return c

    # prefix match against all bundled templates
    for t in sorted(_BUNDLED_TEMPLATES.glob("*.j2")):
        if _short_name(t).startswith(value):
            return t

    available = ", ".join(
        f"'{_short_name(t)}'" for t in sorted(_BUNDLED_TEMPLATES.glob("*.j2"))
    )
    print(
        f"[!] Template '{value}' not found as a file or bundled name.\n"
        f"    Available bundled names: {available}\n"
        f"    Run --list-templates to see full paths.",
        file=sys.stderr,
    )
    sys.exit(1)


def main():
    args = parse_args()

    # --list-controls: show bundled YAML paths and exit
    if getattr(args, "list_controls", False):
        print("Bundled controls files (pass these to --controls):")
        for f in sorted(_BUNDLED_CONTROLS.glob("*.yaml")):
            print(f"  {f}")
        sys.exit(0)

    # --list-templates: show bundled template names and paths and exit
    if getattr(args, "list_templates", False):
        print("Bundled report templates (use the short name with --template):\n")
        for t in sorted(_BUNDLED_TEMPLATES.glob("*.j2")):
            print(f"  {_short_name(t):<16}  {t}")
        print(f"\nExample:  mfaudit --controls controls.yaml --template terminal")
        sys.exit(0)

    if not args.controls:
        print("[!] --controls is required. Use --list-controls to see bundled file paths.", file=sys.stderr)
        sys.exit(1)

    # Validate controls file(s)
    controls_paths = [Path(p) for p in args.controls]
    for cp in controls_paths:
        if not cp.exists():
            print(f"[!] Controls file not found: {cp}", file=sys.stderr)
            sys.exit(1)

    # Validate output dir
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Validate / resolve input files.
    # For --setropts and --irrdbu00 the parser supplies a default filename.
    # If that default doesn't exist on disk we treat the source as absent
    # (controls that need it will be SKIPped).  If the user explicitly
    # supplied a path that doesn't exist we still abort with an error.
    _SETROPTS_DEFAULT = "SETROPTS"
    _IRRDBU00_DEFAULT = "IRRDBU00"

    if args.setropts == _SETROPTS_DEFAULT and not Path(args.setropts).exists():
        print(f"[i] No SETROPTS file found at default path '{_SETROPTS_DEFAULT}' — controls requiring SETROPTS will be SKIP.", file=sys.stderr)
        args.setropts = None
    elif args.setropts and not Path(args.setropts).exists():
        print(f"[!] SETROPTS file not found: {args.setropts}", file=sys.stderr)
        sys.exit(1)

    if args.irrdbu00 == _IRRDBU00_DEFAULT and not Path(args.irrdbu00).exists():
        print(f"[i] No IRRDBU00 file found at default path '{_IRRDBU00_DEFAULT}' — controls requiring IRRDBU00 will be SKIP.", file=sys.stderr)
        args.irrdbu00 = None
    elif args.irrdbu00 and not Path(args.irrdbu00).exists():
        print(f"[!] IRRDBU00 file not found: {args.irrdbu00}", file=sys.stderr)
        sys.exit(1)

    if args.dcollect and not Path(args.dcollect).exists():
        print(f"[!] DCOLLECT file not found: {args.dcollect}", file=sys.stderr)
        sys.exit(1)

    if args.template:
        args.template = str(_resolve_template(args.template))

    # Report date
    report_date = args.report_date or date.today().isoformat()

    print(f"\nMFAudit – RACF CIS Benchmark Audit")
    print(f"System : {args.system_name}")
    print(f"Date   : {report_date}")
    controls_label = ", ".join(str(p) for p in controls_paths)
    print(f"Controls: {controls_label}\n")

    # Load data sources
    setropts = load_setropts(args.setropts)
    irrdbu00 = load_irrdbu00(args.irrdbu00)
    dcollect = load_dcollect(args.dcollect)

    # Load and merge controls from all files
    controls = []
    for cp in controls_paths:
        with open(cp, "r", encoding="utf-8") as fh:
            ctrl_doc = yaml.safe_load(fh)
        batch = ctrl_doc.get("controls", [])
        print(f"[+] Loaded {len(batch)} control(s) from {cp}")
        controls.extend(batch)
    print(f"[+] Total: {len(controls)} control(s)\n")

    # Execute controls
    results = []
    for ctrl in controls:
        cid   = ctrl.get("control_id", "?")
        title = ctrl.get("title", "")
        print(f"  [{cid}] {title[:70]}", end=" ... ", flush=True)

        try:
            status, detail, findings = run_control(ctrl, setropts, irrdbu00, dcollect)
        except Exception as exc:
            status  = STATUS_ERROR
            detail  = str(exc)
            findings = []

        icon = {"PASS": "✓", "FAIL": "✗", "REVIEW": "?", "SKIP": "–", "ERROR": "!"}.get(status, "?")
        print(f"{icon} {status}")
        if detail:
            print(f"    {detail}")

        custom_block = ctrl.get("custom", {})
        results.append({
            "control_id":        cid,
            "title":             title,
            "cis_section":       ctrl.get("cis", {}).get("section", ""),
            "cis_level":         ctrl.get("cis", {}).get("level", ""),
            "custom_benchmark":  custom_block.get("benchmark", ""),
            "custom_category":   custom_block.get("category", ""),
            "custom_reference":  custom_block.get("reference", ""),
            "severity":          (ctrl.get("stig", {}).get("severity", "")
                                  or ctrl.get("severity", "")),
            "stig_rule_id":      ctrl.get("stig", {}).get("rule_id", ""),
            "requirement":       (ctrl.get("stig", {}).get("requirement_excerpt", "")
                                  or ctrl.get("requirement", "")),
            "remediation":       ctrl.get("remediation", ""),
            "data_sources_needed": ctrl.get("data_sources_needed", []),
            "status":            status,
            "detail":            detail,
            "findings":          findings,
        })

    # Summary
    passed  = sum(1 for r in results if r["status"] == STATUS_PASS)
    failed  = sum(1 for r in results if r["status"] == STATUS_FAIL)
    review  = sum(1 for r in results if r["status"] == STATUS_REVIEW)
    skipped = sum(1 for r in results if r["status"] == STATUS_SKIP)
    total   = len(results)
    checked = total - skipped

    print(f"\n{'─'*60}")
    print(f"Results: {passed} PASS  |  {failed} FAIL  |  {review} REVIEW  |  {skipped} SKIP")
    if checked > 0:
        print(f"Score:   {passed}/{checked} = {int(passed/checked*100)}%")
    print(f"{'─'*60}\n")

    # Anonymize if requested
    if args.anonymize:
        print("[~] Anonymizing findings (user IDs, group names, profile names) ...")
        results = anonymize_results(results, irrdbu00=irrdbu00)
        print("    Done — all identifiers replaced with stable labels.\n")

    # Render outputs
    render_report(results, args.system_name, report_date, out_dir, controls_label,
                  anonymized=args.anonymize,
                  template_path=args.template,
                  output_formats=args.format)
    print("\nDone.")


if __name__ == "__main__":
    main()
