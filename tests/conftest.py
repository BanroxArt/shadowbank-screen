from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Any

from shadowbank.model import Entity, Party, Wire
from shadowbank.normalize import entity_key


def party(name: str, reg: str = "", bank: str = "", eid: str = "", **kw: Any) -> Party:
    return Party(
        entity_id=eid or entity_key(name, reg),
        name=name,
        reg_country=reg,
        bank_country=bank,
        bank_name=kw.get("bank_name", ""),
        address=kw.get("address", ""),
    )


_n = 0


def wire(
    orig: Party,
    bene: Party,
    amount: int | str = 100_000,
    when: date = date(2026, 3, 1),
    purpose: str = "freight charter for bulk cargo",
    customer: str = "originator",
    wid: str = "",
) -> Wire:
    global _n
    _n += 1
    return Wire(
        id=wid or f"T{_n:05d}",
        date=when,
        amount_usd=Decimal(str(amount)),
        originator=orig,
        beneficiary=bene,
        purpose=purpose,
        customer=customer,
    )


def entity(eid: str, **kw: Any) -> Entity:
    return Entity(entity_id=eid, **kw)


def codes(findings: Any, role: str | None = None) -> set[str]:
    return {f.code for f in findings if role is None or f.role == role}
