# Eisvogel pandoc template — install & use

[Eisvogel](https://github.com/Wandmalfarbe/pandoc-latex-template) is a clean,
professional pandoc **LaTeX** template (title page, headers/footers, syntax-
highlighted code, callout boxes). It renders Markdown → PDF via a LaTeX engine
(`xelatex` recommended), so it needs LaTeX installed — `wkhtmltopdf` cannot use it.

## 1. Install the dependencies

**Debian / Kali / Ubuntu:**

```bash
sudo apt-get update
sudo apt-get install -y pandoc \
  texlive-xetex texlive-latex-extra texlive-fonts-recommended texlive-fonts-extra
```

- `texlive-xetex` → the `xelatex` engine.
- `texlive-latex-extra` → packages eisvogel uses (e.g. `awesomebox`, `mdframed`).
- the font sets → the default fonts and emoji/symbol coverage.

**macOS:** `brew install pandoc` and a TeX distribution (`brew install --cask
mactex-no-gui`, or the smaller BasicTeX plus `tlmgr install awesomebox mdframed
sourcesanspro sourcecodepro`).

Verify: `pandoc --version` and `xelatex --version` both succeed.

## 2. Install the template

Pandoc looks for templates in its **user data directory** under `templates/`.
Derive it and drop `eisvogel.latex` there. Pin a release and verify it:

```bash
TPL_DIR="$(pandoc --version | awk -F': ' '/User data directory/{print $2}')/templates"
mkdir -p "$TPL_DIR"

# Pinned release (check the releases page for the current version):
VER=3.2.0
TMP="$(mktemp -d)"
curl -fsSL -o "$TMP/eisvogel.tar.gz" \
  "https://github.com/Wandmalfarbe/pandoc-latex-template/releases/download/v${VER}/Eisvogel.tar.gz"
# (optional but recommended) verify against the checksum published on the release page
tar -xzf "$TMP/eisvogel.tar.gz" -C "$TMP"
cp "$(find "$TMP" -name 'eisvogel.latex' | head -1)" "$TPL_DIR/eisvogel.latex"
rm -rf "$TMP"

ls "$TPL_DIR/eisvogel.latex"   # confirm it landed
```

Notes:
- Treat the download as untrusted: pin `VER`, and verify the published checksum
  before copying. Don't pipe it into a shell.
- Older releases ship `eisvogel.tex` instead of `eisvogel.latex`; the wrapper's
  `find_template` accepts either name.
- The template name pandoc uses is the filename stem: `eisvogel`.

## 3. Use it

Directly with pandoc:

```bash
pandoc report.md -o report.pdf --template eisvogel --pdf-engine=xelatex --listings
```

Through this skill (does the engine/listings wiring and checks for you):

```bash
python3 scripts/md_to_pdf.py report.md --eisvogel
python3 scripts/md_to_pdf.py report.md --eisvogel --toc -M titlepage=true
```

## 4. Title page & options (Markdown front matter)

Eisvogel is driven by YAML metadata at the top of the Markdown file:

```yaml
---
title: "Penetration Test Report"
subtitle: "Engagement ENG-2026-001"
author: "pentester agent"
date: "2026-10-17"
titlepage: true
titlepage-color: "1F2430"
titlepage-text-color: "FFFFFF"
toc: true
toc-own-page: true
listings: true
---
```

Common eisvogel variables: `titlepage`, `titlepage-color`,
`titlepage-text-color`, `titlepage-rule-color`, `logo`, `logo-width`,
`book` (chapter layout), `toc-own-page`, `code-block-font-size`. The full list is
in the eisvogel README.

## Troubleshooting

- **`File 'awesomebox.sty' not found`** (or similar) → missing TeX package; install
  `texlive-latex-extra` (apt) or `tlmgr install awesomebox` (mactex/BasicTeX).
- **`pdf-engine xelatex not found`** → install `texlive-xetex`.
- **`Could not find template eisvogel`** → the file isn't in `<user data
  dir>/templates/`; re-check step 2 (`pandoc --version` shows the dir).
- **Emoji/symbols missing** → install `texlive-fonts-extra`.
