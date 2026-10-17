"""Tests for md_to_pdf. Stdlib + pytest; no pandoc/LaTeX/network needed."""
import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "markdown-to-pdf" / "scripts" / "md_to_pdf.py"


def _load():
    spec = importlib.util.spec_from_file_location("md_to_pdf", SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["md_to_pdf"] = mod
    spec.loader.exec_module(mod)
    return mod


mp = _load()


# ---- engine resolution ----
def test_resolve_engine_explicit_wins():
    assert mp.resolve_engine("xelatex", None) == "xelatex"
    assert mp.resolve_engine("wkhtmltopdf", "eisvogel") == "wkhtmltopdf"


def test_resolve_engine_template_forces_latex():
    assert mp.resolve_engine("auto", "eisvogel") == "xelatex"


def test_resolve_engine_auto_prefers_wkhtmltopdf(monkeypatch):
    monkeypatch.setattr(mp.shutil, "which", lambda b: "/usr/bin/wkhtmltopdf" if b == "wkhtmltopdf" else None)
    assert mp.resolve_engine("auto", None) == "wkhtmltopdf"


def test_resolve_engine_auto_falls_back_to_latex(monkeypatch):
    monkeypatch.setattr(mp.shutil, "which", lambda b: "/usr/bin/xelatex" if b == "xelatex" else None)
    assert mp.resolve_engine("auto", None) == "xelatex"


# ---- command building ----
def test_build_command_basic():
    cmd = mp.build_command(Path("r.md"), Path("r.pdf"), "wkhtmltopdf", None,
                           False, None, None, False, False)
    assert cmd[:4] == ["pandoc", "r.md", "-o", "r.pdf"]
    assert "--pdf-engine=wkhtmltopdf" in cmd
    assert "--template" not in cmd


def test_build_command_eisvogel_full():
    cmd = mp.build_command(Path("r.md"), Path("r.pdf"), "xelatex", "eisvogel",
                           True, ["titlepage=true", "title=Report"], "tango", True, True)
    assert "--template" in cmd and "eisvogel" in cmd
    assert "--toc" in cmd and "--number-sections" in cmd and "--listings" in cmd
    assert cmd.count("-M") == 2
    i = cmd.index("--highlight-style")
    assert cmd[i + 1] == "tango"


# ---- template discovery ----
def test_find_template(tmp_path, monkeypatch):
    tdir = tmp_path / "templates"
    tdir.mkdir()
    (tdir / "eisvogel.latex").write_text("% template")
    monkeypatch.setattr(mp, "pandoc_user_templates_dirs", lambda: [tdir])
    assert mp.find_template("eisvogel") == tdir / "eisvogel.latex"
    assert mp.find_template("missing") is None


# ---- CLI ----
def test_dry_run_prints_command(capsys):
    rc = mp.main(["report.md", "--engine", "wkhtmltopdf", "--dry-run"])
    out = capsys.readouterr().out
    assert rc == 0
    assert "pandoc report.md -o report.pdf --pdf-engine=wkhtmltopdf" in out


def test_dry_run_eisvogel_shortcut(capsys):
    rc = mp.main(["report.md", "--eisvogel", "--dry-run"])
    out = capsys.readouterr().out
    assert rc == 0 and "--template eisvogel" in out and "--pdf-engine=xelatex" in out
    assert "--listings" in out        # implied by eisvogel on a LaTeX engine


def test_missing_input_exit_3(tmp_path):
    assert mp.main([str(tmp_path / "nope.md"), "--engine", "wkhtmltopdf"]) == 3


def test_missing_pandoc_exit_3(tmp_path, monkeypatch):
    f = tmp_path / "r.md"
    f.write_text("# hi")
    monkeypatch.setattr(mp.shutil, "which", lambda b: None)
    assert mp.main([str(f), "--engine", "wkhtmltopdf"]) == 3


def test_missing_template_exit_3(tmp_path, monkeypatch):
    f = tmp_path / "r.md"
    f.write_text("# hi")
    monkeypatch.setattr(mp.shutil, "which", lambda b: f"/usr/bin/{b}")   # pandoc + engine present
    monkeypatch.setattr(mp, "find_template", lambda n: None)             # but template missing
    assert mp.main([str(f), "--eisvogel"]) == 3


def test_success(tmp_path, monkeypatch, capsys):
    f = tmp_path / "r.md"
    f.write_text("# hi")
    monkeypatch.setattr(mp.shutil, "which", lambda b: f"/usr/bin/{b}")
    monkeypatch.setattr(mp, "_run", lambda cmd: subprocess.CompletedProcess(cmd, 0, "", ""))
    rc = mp.main([str(f), "--engine", "wkhtmltopdf"])
    assert rc == 0 and "wrote" in capsys.readouterr().out


def test_pandoc_error_exit_2(tmp_path, monkeypatch):
    f = tmp_path / "r.md"
    f.write_text("# hi")
    monkeypatch.setattr(mp.shutil, "which", lambda b: f"/usr/bin/{b}")
    monkeypatch.setattr(mp, "_run", lambda cmd: subprocess.CompletedProcess(cmd, 1, "", "boom"))
    assert mp.main([str(f), "--engine", "wkhtmltopdf"]) == 2
