from __future__ import annotations

import json
from pathlib import Path

import pytest

from shadowbank.cli import main

EX = Path(__file__).resolve().parents[1] / "examples"
COMMON = [
    str(EX / "wires.csv"),
    "--entities",
    str(EX / "entities.csv"),
    "--ledger",
    str(EX / "ledger.csv"),
    "--registry",
    str(EX / "registry.txt"),
]


def test_screen_text_exit_1_when_review(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["screen", *COMMON]) == 1
    out = capsys.readouterr().out
    assert out.splitlines()[0].startswith("1640 wires: ")
    assert "REVIEW" in out and "why:" in out


def test_screen_json_has_clusters_and_sources(capsys: pytest.CaptureFixture[str]) -> None:
    main(["screen", *COMMON, "--format", "json"])
    data = json.loads(capsys.readouterr().out)
    assert data["wires"][0]["disposition"] == "review"
    assert data["clusters"] and data["clusters"][0]["id"] == "C001"
    assert all("FinCEN" in f["source"] or "own" in f["source"] for w in data["wires"] for f in w["findings"])


def test_screen_csv(capsys: pytest.CaptureFixture[str]) -> None:
    main(["screen", *COMMON, "--format", "csv"])
    lines = capsys.readouterr().out.splitlines()
    assert lines[0].startswith("wire_id,date,amount_usd,disposition,code")
    assert len(lines) > 1640


def test_screen_exit_0_when_nothing_for_review(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    p = tmp_path / "w.csv"
    p.write_text("id,date,amount_usd,orig_name,bene_name,purpose\nW1,2026-01-01,10,A,B,rice\n")
    assert main(["screen", str(p)]) == 0
    assert "not evaluated" in capsys.readouterr().out


def test_bad_input_exit_2(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    p = tmp_path / "w.csv"
    p.write_text("id,date,amount_usd,orig_name,bene_name\nW1,bad,10,A,B\n")
    assert main(["screen", str(p)]) == 2
    assert "bad date" in capsys.readouterr().err
    assert main(["screen", str(tmp_path / "missing.csv")]) == 2


def test_network(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["network", *COMMON]) == 0
    assert "C001" in capsys.readouterr().out
    main(["network", *COMMON, "--json"])
    assert json.loads(capsys.readouterr().out)[0]["links"]


def test_develop(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["develop", str(EX / "cases.csv")]) == 0
    out = capsys.readouterr().out
    assert "total" in out and "age-to-age" in out
    assert (
        main(["develop", str(EX / "cases.csv"), "--period", "quarter", "--as-of", "2026-06-30", "--json"])
        == 0
    )
    data = json.loads(capsys.readouterr().out)
    assert data["origins"][-1]["origin"] == "2026-Q2"
    assert any("left out" in n for n in data["notes"])


def test_develop_missing_column(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    p = tmp_path / "c.csv"
    p.write_text("txn_date,amount_usd\n2026-01-01,5\n")
    assert main(["develop", str(p)]) == 2
    assert "missing column" in capsys.readouterr().err


def test_calibrate(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["calibrate", *COMMON, str(EX / "labels.csv")]) == 0
    out = capsys.readouterr().out
    assert "labelled wires" in out and "min_families" in out


def test_calibrate_bad_label(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    p = tmp_path / "l.csv"
    p.write_text("wire_id,label\nW000001,yes\n")
    assert main(["calibrate", *COMMON, str(p)]) == 2


def test_codes(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["codes"]) == 0
    assert "SB-CORRIDOR" in capsys.readouterr().out
