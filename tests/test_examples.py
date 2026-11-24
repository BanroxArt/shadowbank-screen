from __future__ import annotations

import csv
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_examples_are_reproducible(tmp_path: Path) -> None:
    subprocess.run([sys.executable, str(ROOT / "examples" / "make_examples.py"), str(tmp_path)], check=True)
    for name in ["wires.csv", "entities.csv", "ledger.csv", "cases.csv", "labels.csv", "registry.txt"]:
        assert (tmp_path / name).read_bytes() == (ROOT / "examples" / name).read_bytes(), name


def test_example_names_are_invented() -> None:
    rows = list(csv.DictReader((ROOT / "examples" / "entities.csv").open(encoding="utf-8")))
    assert len(rows) == 180
    for r in rows:
        assert r["website"] in {"", f"{r['name'].split()[0].lower()}.example", "tenant.example"}
    banks = {
        r["orig_bank_name"] for r in csv.DictReader((ROOT / "examples" / "wires.csv").open(encoding="utf-8"))
    }
    assert all(b == "" or b.startswith("Synth ") for b in banks)


def _blocks(text: str) -> list[str]:
    return text.split("```")[1::2]


def test_readme_outputs_match_the_tool() -> None:
    from shadowbank.cli import main

    readme = (ROOT / "README.md").read_text()
    blocks = _blocks(readme)
    screen_out = next(b for b in blocks if b.lstrip().startswith("1640 wires"))
    develop_out = next(b for b in blocks if b.lstrip().startswith("origin"))
    ex = ROOT / "examples"
    import contextlib
    import io

    def run(args: list[str]) -> str:
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            main(args)
        return buf.getvalue()

    real = run(
        [
            "screen",
            str(ex / "wires.csv"),
            "--entities",
            str(ex / "entities.csv"),
            "--ledger",
            str(ex / "ledger.csv"),
            "--registry",
            str(ex / "registry.txt"),
        ]
    )
    for line in screen_out.strip("\n").splitlines():
        if line.strip() in {"...", ""}:
            continue
        probe = line.rstrip()[:-3] if line.rstrip().endswith("...") else line.rstrip()
        assert probe in real, line
    real_dev = run(["develop", str(ex / "cases.csv"), "--period", "month"])
    for line in develop_out.strip("\n").splitlines():
        if line.strip() == "...":
            continue
        assert line.rstrip() in real_dev, line
