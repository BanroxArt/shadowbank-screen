"""Input records and their readers.

Three inputs, all CSV or JSON Lines with flat keys (see docs/format.md):

- wires: one row per funds transfer, with both parties inline;
- entities: optional profile rows keyed by ``entity_id``;
- ledger: optional account postings with a category, for the operating-expense check.

Money is held as ``Decimal`` so totals add up to the cent. Countries are ISO 3166-1 alpha-2,
upper case; an empty string means unknown, which is not the same as "no country".
"""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterable, Iterator, Mapping
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path

from .normalize import entity_key


class InputError(ValueError):
    """A row that cannot be read. The message names the source and row."""


@dataclass(frozen=True)
class Party:
    entity_id: str
    name: str
    reg_country: str = ""
    bank_country: str = ""
    bank_name: str = ""
    address: str = ""


@dataclass(frozen=True)
class Wire:
    id: str
    date: date
    amount_usd: Decimal
    originator: Party
    beneficiary: Party
    purpose: str = ""
    # Which side is the reporting institution's customer: "originator", "beneficiary" or "".
    customer: str = ""


@dataclass(frozen=True)
class Entity:
    entity_id: str
    name: str = ""
    reg_country: str = ""
    free_zone: str = ""
    address: str = ""
    incorporated: date | None = None
    # None: unknown. "": checked, nothing found. Anything else: the site.
    website: str | None = None
    owners_disclosed: bool | None = None
    line_of_business: str = ""
    extra: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class LedgerEntry:
    entity_id: str
    date: date
    amount_usd: Decimal
    category: str


def iter_rows(path: Path) -> Iterator[tuple[int, dict[str, str]]]:
    text = path.read_text(encoding="utf-8-sig")
    if path.suffix.lower() in {".jsonl", ".ndjson"}:
        for n, line in enumerate(text.splitlines(), 1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as exc:
                raise InputError(f"{path.name}:{n}: not JSON ({exc.msg})") from None
            if not isinstance(obj, dict):
                raise InputError(f"{path.name}:{n}: expected an object")
            yield n, {str(k): "" if v is None else str(v) for k, v in obj.items()}
    else:
        reader = csv.DictReader(io.StringIO(text))
        for n, row in enumerate(reader, 2):
            yield n, {k.strip(): (v or "").strip() for k, v in row.items() if k is not None}


def _date(raw: str, where: str) -> date:
    try:
        return date.fromisoformat(raw.strip()[:10])
    except ValueError:
        raise InputError(f"{where}: bad date {raw!r}") from None


def _money(raw: str, where: str) -> Decimal:
    cleaned = raw.replace(",", "").replace("$", "").strip()
    try:
        value = Decimal(cleaned)
    except InvalidOperation:
        raise InputError(f"{where}: bad amount {raw!r}") from None
    if not value.is_finite():
        raise InputError(f"{where}: bad amount {raw!r}")
    return value


def _country(raw: str) -> str:
    c = raw.strip().upper()
    return c if len(c) == 2 and c.isalpha() else ""


def _bool(raw: str) -> bool | None:
    v = raw.strip().lower()
    if v in {"1", "true", "yes", "y"}:
        return True
    if v in {"0", "false", "no", "n"}:
        return False
    return None


def _party(row: Mapping[str, str], prefix: str) -> Party:
    name = row.get(f"{prefix}_name", "").strip()
    reg = _country(row.get(f"{prefix}_reg_country", ""))
    eid = row.get(f"{prefix}_id", "").strip() or entity_key(name, reg)
    return Party(
        entity_id=eid,
        name=name,
        reg_country=reg,
        bank_country=_country(row.get(f"{prefix}_bank_country", "")),
        bank_name=row.get(f"{prefix}_bank_name", "").strip(),
        address=row.get(f"{prefix}_address", "").strip(),
    )


def parse_wire(row: Mapping[str, str], where: str) -> Wire:
    wid = row.get("id", "").strip()
    if not wid:
        raise InputError(f"{where}: missing id")
    amount = _money(row.get("amount_usd", ""), where)
    if amount < 0:
        raise InputError(f"{where}: negative amount")
    customer = row.get("customer", "").strip().lower()
    if customer not in {"", "originator", "beneficiary"}:
        raise InputError(f"{where}: customer must be originator, beneficiary or empty")
    orig = _party(row, "orig")
    bene = _party(row, "bene")
    if not orig.name or not bene.name:
        raise InputError(f"{where}: both orig_name and bene_name are required")
    return Wire(
        id=wid,
        date=_date(row.get("date", ""), where),
        amount_usd=amount,
        originator=orig,
        beneficiary=bene,
        purpose=row.get("purpose", "").strip(),
        customer=customer,
    )


def parse_entity(row: Mapping[str, str], where: str) -> Entity:
    name = row.get("name", "").strip()
    reg = _country(row.get("reg_country", ""))
    eid = row.get("entity_id", "").strip() or entity_key(name, reg)
    if not eid:
        raise InputError(f"{where}: entity_id or name is required")
    inc_raw = row.get("incorporated", "").strip()
    web_raw = row.get("website")
    known = {
        "entity_id",
        "name",
        "reg_country",
        "free_zone",
        "address",
        "incorporated",
        "website",
        "owners_disclosed",
        "line_of_business",
    }
    return Entity(
        entity_id=eid,
        name=name,
        reg_country=reg,
        free_zone=row.get("free_zone", "").strip(),
        address=row.get("address", "").strip(),
        incorporated=_date(inc_raw, where) if inc_raw else None,
        website=None if web_raw is None or web_raw.strip() == "?" else web_raw.strip(),
        owners_disclosed=_bool(row.get("owners_disclosed", "")),
        line_of_business=row.get("line_of_business", "").strip(),
        extra={k: v for k, v in row.items() if k not in known and v},
    )


def parse_ledger(row: Mapping[str, str], where: str) -> LedgerEntry:
    eid = row.get("entity_id", "").strip()
    if not eid:
        raise InputError(f"{where}: missing entity_id")
    return LedgerEntry(
        entity_id=eid,
        date=_date(row.get("date", ""), where),
        amount_usd=_money(row.get("amount_usd", ""), where),
        category=row.get("category", "").strip().lower(),
    )


def read_wires(path: Path) -> list[Wire]:
    wires = [parse_wire(r, f"{path.name}:{n}") for n, r in iter_rows(path)]
    seen: set[str] = set()
    for w in wires:
        if w.id in seen:
            raise InputError(f"{path.name}: duplicate wire id {w.id!r}")
        seen.add(w.id)
    return wires


def read_entities(path: Path) -> dict[str, Entity]:
    out: dict[str, Entity] = {}
    for n, r in iter_rows(path):
        e = parse_entity(r, f"{path.name}:{n}")
        if e.entity_id in out:
            raise InputError(f"{path.name}:{n}: duplicate entity_id {e.entity_id!r}")
        out[e.entity_id] = e
    return out


def read_ledger(path: Path) -> list[LedgerEntry]:
    return [parse_ledger(r, f"{path.name}:{n}") for n, r in iter_rows(path)]


def read_lines(path: Path) -> list[str]:
    """One value per line; blank lines and lines starting with # are skipped."""
    return [
        ln.strip()
        for ln in path.read_text(encoding="utf-8").splitlines()
        if ln.strip() and not ln.lstrip().startswith("#")
    ]


def parties(wires: Iterable[Wire]) -> Iterator[Party]:
    for w in wires:
        yield w.originator
        yield w.beneficiary
