from __future__ import annotations

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from shadowbank.model import InputError, read_entities, read_ledger, read_lines, read_wires

HEADER = (
    "id,date,amount_usd,orig_name,orig_reg_country,orig_bank_country,"
    "bene_name,bene_reg_country,purpose,customer\n"
)


def write(tmp: Path, name: str, text: str) -> Path:
    p = tmp / name
    p.write_text(text, encoding="utf-8")
    return p


def test_reads_csv_wires_and_derives_ids(tmp_path: Path) -> None:
    p = write(
        tmp_path,
        "w.csv",
        HEADER + 'W1,2026-03-01,"$1,250,000.50",Varnel Trading Co Ltd,hk,CN,Tusket DMCC,AE,,originator\n',
    )
    (w,) = read_wires(p)
    assert w.amount_usd == Decimal("1250000.50")
    assert w.originator.entity_id == "VARNEL TRADING|HK"
    assert w.originator.reg_country == "HK" and w.originator.bank_country == "CN"
    assert w.beneficiary.entity_id == "TUSKET|AE"
    assert w.date == date(2026, 3, 1)


def test_reads_jsonl(tmp_path: Path) -> None:
    row = {
        "id": "W1",
        "date": "2026-03-01T10:00:00Z",
        "amount_usd": 5,
        "orig_name": "A",
        "bene_name": "B",
        "bene_id": None,
    }
    p = write(tmp_path, "w.jsonl", json.dumps(row) + "\n\n")
    (w,) = read_wires(p)
    assert w.beneficiary.entity_id == "B" and w.date == date(2026, 3, 1)


@pytest.mark.parametrize(
    ("line", "msg"),
    [
        (",2026-03-01,5,A,,,B,,,", "missing id"),
        ("W1,2026-13-01,5,A,,,B,,,", "bad date"),
        ("W1,2026-03-01,five,A,,,B,,,", "bad amount"),
        ("W1,2026-03-01,NaN,A,,,B,,,", "bad amount"),
        ("W1,2026-03-01,-5,A,,,B,,,", "negative"),
        ("W1,2026-03-01,5,A,,,,,,", "both orig_name and bene_name"),
        ("W1,2026-03-01,5,A,,,B,,,payer", "customer must be"),
    ],
)
def test_bad_rows_name_the_row(tmp_path: Path, line: str, msg: str) -> None:
    p = write(tmp_path, "w.csv", HEADER + line + "\n")
    with pytest.raises(InputError, match=msg) as exc:
        read_wires(p)
    assert "w.csv:2" in str(exc.value)


def test_duplicate_ids_rejected(tmp_path: Path) -> None:
    p = write(tmp_path, "w.csv", HEADER + "W1,2026-03-01,5,A,,,B,,,\nW1,2026-03-02,5,A,,,B,,,\n")
    with pytest.raises(InputError, match="duplicate"):
        read_wires(p)


def test_bad_json_line(tmp_path: Path) -> None:
    with pytest.raises(InputError, match="not JSON"):
        read_wires(write(tmp_path, "w.jsonl", "{oops\n"))
    with pytest.raises(InputError, match="expected an object"):
        read_wires(write(tmp_path, "w2.jsonl", "[1]\n"))


def test_entities_tristate_fields(tmp_path: Path) -> None:
    p = write(
        tmp_path,
        "e.csv",
        "entity_id,name,website,owners_disclosed,incorporated,note\n"
        "a,A,,no,2026-01-02,x\nb,B,?,maybe,,\nc,C,c.example,yes,,\n",
    )
    e = read_entities(p)
    assert (
        e["a"].website == "" and e["a"].owners_disclosed is False and e["a"].incorporated == date(2026, 1, 2)
    )
    assert e["a"].extra == {"note": "x"}
    assert e["b"].website is None and e["b"].owners_disclosed is None
    assert e["c"].website == "c.example" and e["c"].owners_disclosed is True


def test_entities_without_website_column_is_unknown(tmp_path: Path) -> None:
    e = read_entities(write(tmp_path, "e.csv", "entity_id,name\na,A\n"))
    assert e["a"].website is None


def test_entities_duplicates_and_missing_id(tmp_path: Path) -> None:
    with pytest.raises(InputError, match="duplicate"):
        read_entities(write(tmp_path, "e.csv", "entity_id,name\na,A\na,B\n"))
    with pytest.raises(InputError, match="required"):
        read_entities(write(tmp_path, "e2.csv", "entity_id,name\n,\n"))


def test_ledger_and_lines(tmp_path: Path) -> None:
    (le,) = read_ledger(
        write(tmp_path, "l.csv", "entity_id,date,amount_usd,category\na,2026-01-01,-5,Payroll\n")
    )
    assert le.category == "payroll" and le.amount_usd == Decimal(-5)
    with pytest.raises(InputError, match="entity_id"):
        read_ledger(write(tmp_path, "l2.csv", "entity_id,date,amount_usd,category\n,2026-01-01,1,x\n"))
    assert read_lines(write(tmp_path, "r.txt", "# c\n\n one \ntwo\n")) == ["one", "two"]
