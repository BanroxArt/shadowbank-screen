"""Write the synthetic example files.

Every company, address and bank below is invented from random syllables; none is a real
party. The data has one planted network built from the FTA findings (Hong Kong companies banking
in mainland China paying UAE free-zone companies that share a tower, Marshall Islands shells at one
registry address, young companies with no website and undisclosed owners, multimillion wires with
no stated purpose, no operating expenses) inside ordinary trade between ordinary companies, some
of which also sit in the UAE, Hong Kong and Singapore.

    python examples/make_examples.py [outdir] [--scale N]
"""

from __future__ import annotations

import csv
import random
import sys
from datetime import date, timedelta
from pathlib import Path

SYL = [
    "var",
    "nel",
    "tus",
    "ket",
    "dor",
    "vin",
    "mar",
    "qua",
    "lio",
    "sen",
    "rho",
    "tal",
    "bry",
    "zen",
    "ock",
    "umi",
]
SECTORS = {
    "shipping": ("Shipping", "freight charter for bulk cargo voyage"),
    "oil": ("Petroleum", "gasoil cargo"),
    "metals": ("Metals", "copper cathode shipment"),
    "technology": ("Electronics", "server components order"),
    "food": ("Foods", "rice consignment"),
    "textiles": ("Textiles", "cotton yarn order"),
}
BANKS = {
    "AE": "Synth Gulf Bank",
    "CN": "Synth Mainland Bank",
    "HK": "Synth Harbour Bank",
    "SG": "Synth Strait Bank",
    "GB": "Synth Thames Bank",
    "CH": "Synth Alpine Bank",
    "DE": "Synth Rhein Bank",
    "US": "Synth Prairie Bank",
    "IN": "Synth Deccan Bank",
    "TR": "Synth Bosphorus Bank",
    "MH": "",
}
CITY = {
    "AE": "Dubai",
    "HK": "Hong Kong",
    "SG": "Singapore",
    "GB": "London",
    "DE": "Hamburg",
    "US": "Houston",
    "IN": "Mumbai",
    "TR": "Istanbul",
    "CN": "Shanghai",
    "MH": "Majuro",
    "CH": "Geneva",
}


def word(rng: random.Random, n: int = 3) -> str:
    return "".join(rng.choice(SYL) for _ in range(n)).capitalize()


def main(argv: list[str]) -> None:
    out = Path(argv[0]) if argv and not argv[0].startswith("--") else Path(__file__).parent
    scale = int(argv[argv.index("--scale") + 1]) if "--scale" in argv else 1
    rng = random.Random(2026)
    out.mkdir(parents=True, exist_ok=True)
    entities: list[dict[str, str]] = []
    start, end = date(2025, 1, 1), date(2026, 8, 31)
    days = (end - start).days

    def add_entity(**kw: str) -> dict[str, str]:
        e = {
            "entity_id": kw["entity_id"],
            "name": kw["name"],
            "reg_country": kw["reg_country"],
            "free_zone": kw.get("free_zone", ""),
            "address": kw["address"],
            "incorporated": kw["incorporated"],
            "website": kw.get("website", ""),
            "owners_disclosed": kw.get("owners_disclosed", "yes"),
            "line_of_business": kw["line_of_business"],
            "bank_country": kw["bank_country"],
        }
        entities.append(e)
        return e

    # Ordinary companies.
    ordinary: list[dict[str, str]] = []
    countries = ["AE", "HK", "SG", "GB", "DE", "US", "IN", "TR"]
    for i in range(160 * scale):
        c = rng.choice(countries)
        sector = rng.choice(list(SECTORS))
        label = SECTORS[sector][0]
        nm = f"{word(rng)} {label} Ltd"
        if c == "AE" and rng.random() < 0.4:
            nm = f"{word(rng)} {label} FZE"
        inc = start - timedelta(days=rng.randint(800, 9000))
        if rng.random() < 0.05:
            inc = start + timedelta(days=rng.randint(0, 200))
        ordinary.append(
            add_entity(
                entity_id=f"OK{i:04d}",
                name=nm,
                reg_country=c,
                address=f"{rng.randint(1, 400)} {word(rng, 2)} Street, {CITY[c]}",
                incorporated=inc.isoformat(),
                website=f"{nm.split()[0].lower()}.example",
                line_of_business=f"{sector} {label.lower()}",
                bank_country=c,
            )
        )

    # The planted network.
    tower = f"Tower 7, {word(rng, 2)} Lakes Road, Dubai"
    registry = f"Registry Complex, {word(rng, 2)} Road, Majuro"
    ring: list[dict[str, str]] = []
    for i in range(4 * scale):
        ring.append(
            add_entity(
                entity_id=f"HK{i:03d}",
                name=f"{word(rng)} Trading Co Ltd",
                reg_country="HK",
                address=f"Room {rng.randint(100, 2999)}, {word(rng, 2)} Commercial Building, Hong Kong",
                incorporated=(start + timedelta(days=rng.randint(30, 300))).isoformat(),
                owners_disclosed="no",
                line_of_business="general trading",
                bank_country="CN",
            )
        )
    for i in range(5 * scale):
        ring.append(
            add_entity(
                entity_id=f"AE{i:03d}",
                name=f"{word(rng)} Petroleum DMCC",
                reg_country="AE",
                free_zone="DMCC",
                address=f"Office {rng.randint(100, 3999)}, {tower}",
                incorporated=(start + timedelta(days=rng.randint(0, 250))).isoformat(),
                owners_disclosed="no",
                line_of_business="oil trading",
                bank_country="AE",
            )
        )
    for i in range(9 * scale):
        ring.append(
            add_entity(
                entity_id=f"MH{i:03d}",
                name=f"{word(rng)} Maritime Inc",
                reg_country="MH",
                address=f"Unit {i + 1}, {registry}",
                incorporated=(start + timedelta(days=rng.randint(0, 400))).isoformat(),
                owners_disclosed="no",
                line_of_business="ship owning",
                bank_country=rng.choice(["SG", "AE", "GB"]),
            )
        )
    # Two more tower tenants that are ordinary, to show the shared-building signal on its own.
    for i in range(2):
        ordinary.append(
            add_entity(
                entity_id=f"TW{i:03d}",
                name=f"{word(rng)} Consulting FZE",
                reg_country="AE",
                free_zone="DMCC",
                address=f"Office {rng.randint(100, 3999)}, {tower}",
                incorporated="2015-03-01",
                website="tenant.example",
                line_of_business="management consulting",
                bank_country="AE",
            )
        )

    wires: list[dict[str, str]] = []
    labels: list[tuple[str, int]] = []

    def wire(o: dict[str, str], b: dict[str, str], d: date, amt: int, purpose: str, bad: int) -> None:
        wid = f"W{len(wires) + 1:06d}"
        wires.append(
            {
                "id": wid,
                "date": d.isoformat(),
                "amount_usd": str(amt),
                "orig_id": o["entity_id"],
                "orig_name": o["name"],
                "orig_reg_country": o["reg_country"],
                "orig_bank_country": o["bank_country"],
                "orig_bank_name": BANKS.get(o["bank_country"], ""),
                "orig_address": o["address"],
                "bene_id": b["entity_id"],
                "bene_name": b["name"],
                "bene_reg_country": b["reg_country"],
                "bene_bank_country": b["bank_country"],
                "bene_bank_name": BANKS.get(b["bank_country"], ""),
                "bene_address": b["address"],
                "purpose": purpose,
                "customer": "originator",
            }
        )
        noisy = bad if rng.random() > 0.03 else 1 - bad
        labels.append((wid, noisy))

    for _ in range(1400 * scale):
        o, b = rng.sample(ordinary, 2)
        sector = next((k for k in SECTORS if k in o["line_of_business"]), "")
        purpose = SECTORS[sector][1] if sector else "management consulting fee"
        amt = int(rng.lognormvariate(12.6, 1.1))
        wire(o, b, start + timedelta(days=rng.randint(0, days)), amt, purpose, 0)

    hk = [e for e in ring if e["entity_id"].startswith("HK")]
    ae = [e for e in ring if e["entity_id"].startswith("AE")]
    mh = [e for e in ring if e["entity_id"].startswith("MH")]
    shared_suppliers = rng.sample(ordinary, 6)
    for _ in range(140 * scale):
        o = rng.choice(hk)
        b = rng.choice(ae + mh[:4])
        d = date.fromisoformat(o["incorporated"]) + timedelta(days=rng.randint(5, 330))
        purpose = rng.choice(["", "payment", "goods", "INV 4471", "as per contract", "consulting fee"])
        wire(o, b, min(d, end), rng.randint(1_200_000, 6_500_000), purpose, 1)
    for _ in range(60 * scale):
        o = rng.choice(ae)
        b = rng.choice(mh + shared_suppliers)
        d = date.fromisoformat(o["incorporated"]) + timedelta(days=rng.randint(5, 330))
        wire(o, b, min(d, end), rng.randint(700_000, 4_000_000), rng.choice(["", "settlement", "freight"]), 1)
    for _ in range(40 * scale):
        o = rng.choice(hk)
        b = rng.choice(shared_suppliers)
        d = date.fromisoformat(o["incorporated"]) + timedelta(days=rng.randint(5, 330))
        wire(o, b, min(d, end), rng.randint(600_000, 2_000_000), "goods", 1)

    ledger: list[dict[str, str]] = []
    for e in ordinary:
        for m in range(18):
            d = start + timedelta(days=30 * m + rng.randint(0, 5))
            ledger.append(
                {
                    "entity_id": e["entity_id"],
                    "date": d.isoformat(),
                    "amount_usd": f"-{rng.randint(20, 300)}000",
                    "category": "payroll",
                }
            )
            ledger.append(
                {
                    "entity_id": e["entity_id"],
                    "date": d.isoformat(),
                    "amount_usd": f"{rng.randint(200, 2000)}000",
                    "category": "receipts",
                }
            )
    for w in wires:
        if w["orig_id"][:2] in {"HK", "AE", "MH"}:
            ledger.append(
                {
                    "entity_id": w["orig_id"],
                    "date": w["date"],
                    "amount_usd": f"-{w['amount_usd']}",
                    "category": "wire out",
                }
            )
        if w["bene_id"][:2] in {"HK", "AE", "MH"}:
            ledger.append(
                {
                    "entity_id": w["bene_id"],
                    "date": w["date"],
                    "amount_usd": w["amount_usd"],
                    "category": "wire in",
                }
            )

    cases: list[dict[str, str]] = []
    for _ in range(3000 * scale):
        t = start + timedelta(days=rng.randint(0, days))
        lag = int(rng.expovariate(1 / 95))
        a = t + timedelta(days=lag)
        if a > end:
            continue
        cases.append(
            {
                "txn_date": t.isoformat(),
                "attributed_date": a.isoformat(),
                "amount_usd": str(int(rng.lognormvariate(14.6, 0.8))),
            }
        )

    def write(name: str, rows: list[dict[str, str]]) -> None:
        with (out / name).open("w", newline="", encoding="utf-8") as fh:
            w = csv.DictWriter(fh, fieldnames=list(rows[0]), lineterminator="\n")
            w.writeheader()
            w.writerows(rows)

    write("entities.csv", [{k: v for k, v in e.items() if k != "bank_country"} for e in entities])
    write("wires.csv", wires)
    write("ledger.csv", ledger)
    write("cases.csv", cases)
    write("labels.csv", [{"wire_id": w, "label": str(y)} for w, y in labels])
    (out / "registry.txt").write_text(
        f"# Registry and registered-agent addresses (invented)\n{registry}\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main(sys.argv[1:])
