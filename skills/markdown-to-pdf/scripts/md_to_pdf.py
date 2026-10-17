#!/usr/bin/env python3
"""Convert a Markdown file to PDF with pandoc (general-purpose, offline).

Any agent that writes a Markdown report/answer/notes file can render it to a PDF
with this wrapper. Two engine families:
  - wkhtmltopdf  : HTML-based, lightweight, no LaTeX           (good default)
  - xelatex/...  : LaTeX; required for the `eisvogel` template (polished reports)

It only runs pandoc on local files: no network, no secrets, nothing destructive
beyond writing the output PDF.

Usage:
  md_to_pdf.py REPORT.md                       # -> REPORT.pdf (auto engine)
  md_to_pdf.py REPORT.md -o out.pdf --eisvogel # polished LaTeX template
  md_to_pdf.py REPORT.md --engine wkhtmltopdf --toc
  md_to_pdf.py REPORT.md --eisvogel -M titlepage=true -M 'title=Pentest Report'
  md_to_pdf.py REPORT.md --dry-run             # print the pandoc command only
Exit: 0 ok; 2 pandoc failed; 3 usage / pandoc or engine or template missing.
Stdlib only.
"""
from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

TIMEOUT = 180
LATEX_ENGINES = ("xelatex", "lualatex", "pdflatex", "tectonic")


def resolve_engine(engine: str, template: str | None) -> str:
    """Pick the pandoc --pdf-engine. 'auto' -> xelatex for a template, else wkhtmltopdf."""
    if engine and engine != "auto":
        return engine
    if template:                       # LaTeX templates (eisvogel) need a LaTeX engine
        return "xelatex"
    if shutil.which("wkhtmltopdf"):    # no template: prefer the lightweight HTML engine
        return "wkhtmltopdf"
    for e in LATEX_ENGINES:
        if shutil.which(e):
            return e
    return "wkhtmltopdf"               # nothing found: name it so the error is actionable


def pandoc_user_templates_dirs() -> list[Path]:
    """Where pandoc looks for user templates, most-specific first."""
    dirs: list[Path] = []
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        dirs.append(Path(xdg) / "pandoc" / "templates")
    dirs.append(Path.home() / ".local" / "share" / "pandoc" / "templates")
    dirs.append(Path.home() / ".pandoc" / "templates")       # legacy location
    return dirs


def find_template(name: str) -> Path | None:
    """Locate a pandoc template by name (tries `name`, `name.latex`, `name.tex`)."""
    candidates = [name, f"{name}.latex", f"{name}.tex"]
    for d in pandoc_user_templates_dirs():
        for c in candidates:
            p = d / c
            if p.is_file():
                return p
    return None


def build_command(inp: Path, out: Path, engine: str, template: str | None,
                  toc: bool, metadata: list[str] | None, highlight: str | None,
                  listings: bool, number_sections: bool) -> list[str]:
    """Assemble the pandoc argv (pure; no side effects — the unit-test seam)."""
    cmd = ["pandoc", str(inp), "-o", str(out), f"--pdf-engine={engine}"]
    if template:
        cmd += ["--template", template]
    if toc:
        cmd.append("--toc")
    if number_sections:
        cmd.append("--number-sections")
    if highlight:
        cmd += ["--highlight-style", highlight]
    if listings:
        cmd.append("--listings")
    for kv in metadata or []:
        cmd += ["-M", kv]
    return cmd


def _run(cmd: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="Convert Markdown to PDF via pandoc")
    ap.add_argument("input")
    ap.add_argument("-o", "--output", help="output PDF (default: input with .pdf)")
    ap.add_argument("--engine", default="auto",
                    help="auto|wkhtmltopdf|xelatex|lualatex|pdflatex|tectonic")
    ap.add_argument("--template", help="pandoc template name (e.g. eisvogel)")
    ap.add_argument("--eisvogel", action="store_true",
                    help="shortcut for --template eisvogel (LaTeX; needs xelatex + the template)")
    ap.add_argument("--toc", action="store_true", help="add a table of contents")
    ap.add_argument("--number-sections", action="store_true")
    ap.add_argument("--highlight-style", help="pandoc code highlight style (e.g. tango)")
    ap.add_argument("--listings", action="store_true",
                    help="use the LaTeX listings package for code (implied by --eisvogel)")
    ap.add_argument("-M", "--metadata", action="append", metavar="KEY=VALUE",
                    help="pandoc metadata (repeatable), e.g. -M titlepage=true")
    ap.add_argument("--dry-run", action="store_true", help="print the pandoc command, run nothing")
    args = ap.parse_args(argv)

    inp = Path(args.input)
    out = Path(args.output) if args.output else inp.with_suffix(".pdf")
    template = args.template or ("eisvogel" if args.eisvogel else None)
    engine = resolve_engine(args.engine, template)
    # --listings only affects LaTeX output; eisvogel wants it on.
    listings = (args.listings or template == "eisvogel") and engine in LATEX_ENGINES

    cmd = build_command(inp, out, engine, template, args.toc, args.metadata,
                        args.highlight_style, listings, args.number_sections)

    if args.dry_run:
        print(" ".join(cmd))
        return 0

    if not inp.is_file():
        print(f"error: input not found: {inp}", file=sys.stderr)
        return 3
    if not shutil.which("pandoc"):
        print("error: `pandoc` not installed (apt install pandoc). "
              "See references/eisvogel-setup.md", file=sys.stderr)
        return 3
    if engine != "wkhtmltopdf" and not shutil.which(engine):
        print(f"error: PDF engine '{engine}' not found — install a LaTeX engine "
              f"(e.g. apt install texlive-xetex) or use --engine wkhtmltopdf.",
              file=sys.stderr)
        return 3
    if engine == "wkhtmltopdf" and not shutil.which("wkhtmltopdf"):
        print("error: wkhtmltopdf not found (apt install wkhtmltopdf) — "
              "or choose a LaTeX engine with --engine xelatex.", file=sys.stderr)
        return 3
    if template and find_template(template) is None:
        print(f"error: pandoc template '{template}' not installed. "
              f"See references/eisvogel-setup.md to install it.", file=sys.stderr)
        return 3

    try:
        p = _run(cmd)
    except (subprocess.SubprocessError, OSError) as e:
        print(f"error: pandoc failed: {e}", file=sys.stderr)
        return 2
    if p.returncode != 0:
        sys.stderr.write(p.stderr)
        print(f"error: pandoc exited {p.returncode}", file=sys.stderr)
        return 2
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
