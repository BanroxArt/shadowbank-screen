"""Wire screening against the FinCEN shadow banking findings.

Each check emits a ``Finding`` with a code from ``codes.py``. A wire's disposition comes from how
many independent indicator families fired, never from one country:

- ``review``: a listed bank (``L``), or medium-or-higher findings in two of the entity,
  transaction and network families, or low-or-higher findings in ``min_families`` families of
  which at least one is medium-or-higher outside geography;
- ``watch``: at least one low-or-higher finding outside geography;
- ``note``: geography only;
- ``clear``: nothing above ``info``.

Geography alone never produces ``review``. FinCEN's own figures show why: the UAE, Hong Kong and
Singapore corridors carry a great deal of ordinary trade, and the FTA describes routes in BSA data,
not a list of places to avoid.
"""

from __future__ import annotations

import bisect
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import Decimal
from typing import Final, Literal

from .codes import CODES, SEVERITY_RANK, Family, Severity
from .model import Entity, LedgerEntry, Party, Wire
from .network import neighbours, significant_pairs
from .normalize import (
    COMPATIBLE,
    SECTOR_CATEGORIES,
    building_key,
    categories,
    fold,
    free_zone_marker,
    is_generic_purpose,
    name_key,
)

Role = Literal["originator", "beneficiary", "wire", "run"]
Disposition = Literal["review", "watch", "note", "clear"]

HUB_REG: Final = frozenset({"AE", "HK", "SG"})
HUB_BANK: Final = frozenset({"AE", "CN", "HK", "SG", "GB", "CH"})
OFFSHORE: Final = frozenset({"MH", "VG"})
# Bank-location corridors from FTA p. 3, with FinCEN's approximate totals for the review period.
# "" stands for an unidentified originating jurisdiction.
CORRIDORS: Final[dict[tuple[str, str], str]] = {
    ("CN", "AE"): "about $2.6 billion",
    ("SG", "AE"): "about $981 million",
    ("", "AE"): "$943 million",
    ("GB", "AE"): "about $922 million",
}
COUNTRY_NAMES: Final = {
    "AE": "UAE",
    "CN": "mainland China",
    "HK": "Hong Kong",
    "SG": "Singapore",
    "GB": "United Kingdom",
    "CH": "Switzerland",
    "MH": "Marshall Islands",
    "VG": "British Virgin Islands",
    "": "unidentified",
}
DEFAULT_OPEX: Final = frozenset(
    {"payroll", "salary", "wages", "rent", "utilities", "tax", "insurance", "office", "opex", "benefits"}
)


@dataclass(frozen=True)
class Config:
    scope_min: Decimal = Decimal(500_000)
    sof_min: Decimal = Decimal(1_000_000)
    young_days: int = 365
    colocated_min: int = 5
    burst_min: Decimal = Decimal(1_000_000)
    burst_count: int = 3
    burst_days: int = 30
    shared_min: int = 2
    max_counterparty_degree: int = 50
    shared_p: float = 0.001
    opex_min_flow: Decimal = Decimal(1_000_000)
    opex_min_days: int = 60
    min_families: int = 3
    registry_addresses: frozenset[str] = frozenset()
    opex_categories: frozenset[str] = DEFAULT_OPEX

    def __post_init__(self) -> None:
        for name in ("young_days", "colocated_min", "burst_count", "burst_days", "shared_min"):
            if getattr(self, name) < 1:
                raise ValueError(f"{name} must be at least 1")
        if self.min_families < 2:
            raise ValueError("min_families must be at least 2")


@dataclass(frozen=True)
class Finding:
    code: str
    role: Role
    subject: str
    evidence: str

    @property
    def family(self) -> Family:
        return CODES[self.code][0]

    @property
    def severity(self) -> Severity:
        return CODES[self.code][1]

    @property
    def source(self) -> str:
        return CODES[self.code][2]


@dataclass
class WireResult:
    wire: Wire
    findings: list[Finding]
    disposition: Disposition
    families: list[str]
    reasons: list[str]


@dataclass
class ScreenResult:
    wires: list[WireResult]
    entity_findings: dict[str, list[Finding]]
    run_findings: list[Finding]
    flagged: set[str]
    buildings: dict[str, str]
    hubs: set[str] = field(default_factory=set)


def _profile(party: Party, entities: Mapping[str, Entity]) -> Entity:
    known = entities.get(party.entity_id)
    if known is None:
        return Entity(
            entity_id=party.entity_id, name=party.name, reg_country=party.reg_country, address=party.address
        )
    return Entity(
        entity_id=known.entity_id,
        name=known.name or party.name,
        reg_country=known.reg_country or party.reg_country,
        free_zone=known.free_zone,
        address=known.address or party.address,
        incorporated=known.incorporated,
        website=known.website,
        owners_disclosed=known.owners_disclosed,
        line_of_business=known.line_of_business,
        extra=known.extra,
    )


def _money(v: Decimal) -> str:
    return f"${v:,.0f}"


def _bursts(wires: Iterable[Wire], cfg: Config) -> dict[str, str]:
    """Entity id -> evidence for the densest window that meets the burst rule."""
    by_entity: dict[str, list[tuple[date, Decimal, str]]] = defaultdict(list)
    for w in wires:
        if w.amount_usd >= cfg.burst_min:
            for p in (w.originator, w.beneficiary):
                by_entity[p.entity_id].append((w.date, w.amount_usd, w.id))
    out: dict[str, str] = {}
    span = timedelta(days=cfg.burst_days - 1)
    for eid, items in by_entity.items():
        if len(items) < cfg.burst_count:
            continue
        items.sort()
        dates = [d for d, _, _ in items]
        best: tuple[int, Decimal, date, date] | None = None
        for i, (start, _, _) in enumerate(items):
            j = bisect.bisect_right(dates, start + span)
            n = j - i
            if n >= cfg.burst_count:
                total = sum((a for _, a, _ in items[i:j]), Decimal(0))
                cand = (n, total, start, dates[j - 1])
                if best is None or (cand[0], cand[1]) > (best[0], best[1]):
                    best = cand
        if best is not None:
            n, total, d0, d1 = best
            out[eid] = (
                f"{n} wires of at least {_money(cfg.burst_min)} between {d0} and {d1}, total {_money(total)}"
            )
    return out


def _opex(ledger: Iterable[LedgerEntry], cfg: Config) -> tuple[dict[str, str], set[str]]:
    """Entities whose ledger has large flows and no operating expense, and the entities seen."""
    flow: dict[str, Decimal] = defaultdict(Decimal)
    first: dict[str, date] = {}
    last: dict[str, date] = {}
    opex: dict[str, int] = defaultdict(int)
    for e in ledger:
        flow[e.entity_id] += abs(e.amount_usd)
        first[e.entity_id] = min(first.get(e.entity_id, e.date), e.date)
        last[e.entity_id] = max(last.get(e.entity_id, e.date), e.date)
        if e.category in cfg.opex_categories and e.amount_usd < 0:
            opex[e.entity_id] += 1
    out: dict[str, str] = {}
    for eid, total in flow.items():
        days = (last[eid] - first[eid]).days + 1
        if total >= cfg.opex_min_flow and days >= cfg.opex_min_days and opex[eid] == 0:
            out[eid] = (
                f"{_money(total)} through the account over {days} days, no debit in"
                f" {', '.join(sorted(cfg.opex_categories))}"
            )
    return out, set(flow)


def _is_banque_misr_uae(p: Party) -> bool:
    return p.bank_country == "AE" and name_key(p.bank_name).startswith("BANQUE MISR")


def screen(
    wires: list[Wire],
    entities: Mapping[str, Entity] | None = None,
    ledger: list[LedgerEntry] | None = None,
    cfg: Config | None = None,
) -> ScreenResult:
    cfg = cfg or Config()
    entities = entities or {}
    profiles: dict[str, Entity] = {}
    for w in wires:
        for p in (w.originator, w.beneficiary):
            if p.entity_id not in profiles:
                profiles[p.entity_id] = _profile(p, entities)
    for eid, e in entities.items():
        profiles.setdefault(eid, e)

    buildings = {eid: building_key(e.address) for eid, e in profiles.items()}
    occupants: dict[str, set[str]] = defaultdict(set)
    for eid, key in buildings.items():
        if key:
            occupants[key].add(eid)

    run: list[Finding] = []
    missing = []
    if not entities:
        missing.append("no entities file: SB-YOUNG, SB-NO-WEB, SB-OPAQUE and SB-LOB-MISMATCH did not run")
    if ledger is None:
        missing.append("no ledger: SB-NO-OPEX did not run")
    if not any(w.customer for w in wires):
        missing.append("no customer column: SB-LOB-MISMATCH checked every party with a line of business")
    for m in missing:
        run.append(Finding("SB-SCOPE-NOT-EVALUATED", "run", "run", m))

    bursts = _bursts(wires, cfg)
    no_opex, _ = _opex(ledger or [], cfg)

    # --- entity-level findings ---
    ent: dict[str, list[Finding]] = defaultdict(list)
    for eid, e in profiles.items():

        def add(code: str, evidence: str, eid: str = eid) -> None:
            ent[eid].append(Finding(code, "run", eid, evidence))

        key = buildings[eid]
        n_here = len(occupants.get(key, ()))
        if e.reg_country in {"AE", ""}:
            marker = free_zone_marker(e.name, e.address, e.free_zone)
            if marker and (e.reg_country == "AE" or "DMCC" in marker):
                add("SB-FREEZONE", marker)
        if e.reg_country in OFFSHORE:
            where = COUNTRY_NAMES[e.reg_country]
            if key and key in cfg.registry_addresses:
                add("SB-OFFSHORE-REGISTRY", f"registered in {where}; address is a listed registry address")
            elif key and n_here >= cfg.colocated_min:
                add("SB-OFFSHORE-REGISTRY", f"registered in {where}; {n_here} entities share the address")
            else:
                add("SB-OFFSHORE", f"registered in {where}")
        if key and n_here >= cfg.colocated_min:
            add("SB-COLOCATED", f"{n_here} distinct entities at {key!r}")
        if e.website is not None and e.website == "":
            add("SB-NO-WEB", "website checked, none found")
        if e.owners_disclosed is False:
            add("SB-OPAQUE", "beneficial owners not disclosed")
        sectors = [c for c in categories(f"{e.line_of_business} {e.name}") if c in SECTOR_CATEGORIES]
        if sectors:
            add("SB-SECTOR", ", ".join(sectors))
        if eid in bursts:
            add("SB-BURST", bursts[eid])
        if eid in no_opex:
            add("SB-NO-OPEX", no_opex[eid])

    # --- wire-level findings, first pass ---
    per_wire: list[list[Finding]] = []
    for w in wires:
        f: list[Finding] = []
        if w.amount_usd >= cfg.scope_min:
            f.append(Finding("SB-SCOPE-VALUE", "wire", w.id, f"{_money(w.amount_usd)}"))
        corridor = (w.originator.bank_country, w.beneficiary.bank_country)
        if corridor in CORRIDORS:
            a, b = (COUNTRY_NAMES.get(c, c) for c in corridor)
            f.append(
                Finding("SB-CORRIDOR", "wire", w.id, f"banks {a} to {b}; FinCEN total {CORRIDORS[corridor]}")
            )
        for role, p in (("originator", w.originator), ("beneficiary", w.beneficiary)):
            r: Role = "originator" if role == "originator" else "beneficiary"
            prof = profiles[p.entity_id]
            if prof.reg_country in HUB_REG:
                f.append(
                    Finding("SB-HUB-REG", r, p.entity_id, f"registered in {COUNTRY_NAMES[prof.reg_country]}")
                )
            if p.bank_country in HUB_BANK:
                f.append(Finding("SB-HUB-BANK", r, p.entity_id, f"banks in {COUNTRY_NAMES[p.bank_country]}"))
            if (
                prof.reg_country in HUB_REG
                and p.bank_country
                and p.bank_country != prof.reg_country
                and p.bank_country in HUB_BANK
            ):
                f.append(
                    Finding(
                        "SB-REG-BANK-SPLIT",
                        r,
                        p.entity_id,
                        f"registered in {COUNTRY_NAMES[prof.reg_country]}, banks in"
                        f" {COUNTRY_NAMES[p.bank_country]}",
                    )
                )
            if prof.incorporated is not None:
                age = (w.date - prof.incorporated).days
                if 0 <= age < cfg.young_days:
                    f.append(
                        Finding("SB-YOUNG", r, p.entity_id, f"incorporated {prof.incorporated}, {age} days")
                    )
            if _is_banque_misr_uae(p):
                f.append(
                    Finding(
                        "SB-BANK-311-PROPOSED",
                        r,
                        p.entity_id,
                        f"banks at {p.bank_name!r} in the UAE; proposed rule, check its status before acting",
                    )
                )
            for ef in ent.get(p.entity_id, ()):
                f.append(Finding(ef.code, r, p.entity_id, ef.evidence))
        if w.amount_usd >= cfg.sof_min and is_generic_purpose(w.purpose):
            shown = w.purpose or "(empty)"
            f.append(Finding("SB-SOF-MISSING", "wire", w.id, f"{_money(w.amount_usd)}, purpose {shown!r}"))
        purpose_cats = categories(w.purpose)
        if purpose_cats:
            sides = (
                [w.originator if w.customer == "originator" else w.beneficiary]
                if w.customer
                else [
                    w.originator,
                    w.beneficiary,
                ]
            )
            for p in sides:
                lob = profiles[p.entity_id].line_of_business
                lob_cats = categories(lob)
                if not lob_cats:
                    continue
                allowed: set[str] = set()
                for c in lob_cats:
                    allowed |= COMPATIBLE.get(c, frozenset({c}))
                if not set(purpose_cats) & allowed:
                    r2: Role = "originator" if p is w.originator else "beneficiary"
                    f.append(
                        Finding(
                            "SB-LOB-MISMATCH",
                            r2,
                            p.entity_id,
                            f"purpose {'/'.join(purpose_cats)} vs line of business {fold(lob).lower()!r}",
                        )
                    )
        per_wire.append(f)

    # --- network ---
    flagged: set[str] = set()
    for eid, fs in ent.items():
        if any(x.family in {"E", "T"} and SEVERITY_RANK[x.severity] >= 2 for x in fs):
            flagged.add(eid)
    for w, fs in zip(wires, per_wire, strict=True):
        for x in fs:
            if x.family in {"T", "L"} and SEVERITY_RANK[x.severity] >= 2:
                # A wire-level finding (missing or incomplete source of funds) is about the sender's money.
                flagged.add(w.beneficiary.entity_id if x.role == "beneficiary" else w.originator.entity_id)
            if x.code == "SB-YOUNG":
                flagged.add(x.subject)

    adj = neighbours(wires)
    pairs, hubs = significant_pairs(adj, cfg.max_counterparty_degree, cfg.shared_min, cfg.shared_p)
    shared_with: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for (a, b), (k, _p) in pairs.items():
        if b in flagged:
            shared_with[a].append((b, k))
        if a in flagged:
            shared_with[b].append((a, k))
    net: dict[str, list[Finding]] = defaultdict(list)
    for eid, others in shared_with.items():
        others.sort(key=lambda t: (-t[1], t[0]))
        top = ", ".join(f"{o} ({n})" for o, n in others[:3])
        more = f" and {len(others) - 3} more" if len(others) > 3 else ""
        net[eid].append(Finding("SB-NET-SHARED-CPTY", "run", eid, f"shares counterparties with {top}{more}"))
    for members in occupants.values():
        hit = sorted(members & flagged)
        if not hit or len(members) < 2:
            continue
        for eid in members:
            others2 = [m for m in hit if m != eid]
            if others2:
                net[eid].append(
                    Finding(
                        "SB-NET-SHARED-ADDR", "run", eid, f"same building as flagged {', '.join(others2[:3])}"
                    )
                )
    for eid, fs in net.items():
        ent[eid].extend(fs)

    results: list[WireResult] = []
    for w, fs in zip(wires, per_wire, strict=True):
        for role, p in (("originator", w.originator), ("beneficiary", w.beneficiary)):
            r3: Role = "originator" if role == "originator" else "beneficiary"
            for nf in net.get(p.entity_id, ()):
                fs.append(Finding(nf.code, r3, p.entity_id, nf.evidence))
        disp, fams, reasons = decide(fs, cfg)
        results.append(WireResult(w, fs, disp, fams, reasons))
    return ScreenResult(results, dict(ent), run, flagged, buildings, hubs)


def decide(findings: Iterable[Finding], cfg: Config) -> tuple[Disposition, list[str], list[str]]:
    present: set[str] = set()
    strong: set[str] = set()
    listed = False
    for f in findings:
        rank = SEVERITY_RANK[f.severity]
        if rank >= 1:
            present.add(f.family)
        if rank >= 2 and f.family in {"E", "T", "N"}:
            strong.add(f.family)
        if f.family == "L":
            listed = True
    fams = sorted(present)
    if listed:
        return "review", fams, ["party banks at an institution named in a proposed section 311 rule"]
    if len(strong) >= 2:
        return "review", fams, [f"medium findings in {len(strong)} families: {', '.join(sorted(strong))}"]
    if len(present) >= cfg.min_families and strong:
        return "review", fams, [f"findings in {len(present)} families: {', '.join(fams)}"]
    if present - {"G"}:
        return "watch", fams, [f"findings in {', '.join(fams)}"]
    if present:
        return "note", fams, ["geography only"]
    return "clear", fams, []
