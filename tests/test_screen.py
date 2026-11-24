from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from shadowbank.model import LedgerEntry
from shadowbank.normalize import building_key
from shadowbank.screen import Config, Finding, decide, screen

from .conftest import codes, entity, party, wire

HK = party("Varnel Trading Co Ltd", "HK", "CN", eid="HK1")
AE = party("Tusket Petroleum DMCC", "AE", "AE", eid="AE1")
DE = party("Dorvin Metals GmbH", "DE", "DE", eid="DE1")
US = party("Qualio Foods Inc", "US", "US", eid="US1")


def one(w, **kw):  # type: ignore[no-untyped-def]
    res = screen([w], **kw)
    return res.wires[0]


def test_ordinary_domestic_wire_is_clear() -> None:
    r = one(wire(DE, US, 250_000, purpose="copper cathode shipment"))
    assert r.disposition == "clear"
    assert r.findings == []


def test_geography_alone_is_only_a_note() -> None:
    r = one(wire(HK, AE, 400_000, purpose="gasoil cargo"))
    got = codes(r.findings)
    assert {"SB-CORRIDOR", "SB-HUB-REG", "SB-HUB-BANK", "SB-REG-BANK-SPLIT", "SB-FREEZONE"} <= got
    # FREEZONE is an entity finding, so this is watch, not review.
    assert r.disposition == "watch"
    plain_ae = party("Tusket Petroleum LLC", "AE", "AE", eid="AE9")
    r2 = one(wire(HK, plain_ae, 400_000, purpose="gasoil cargo"))
    assert r2.disposition == "note"
    assert r2.reasons == ["geography only"]


@pytest.mark.parametrize(
    ("o", "b", "hit"),
    [
        ("CN", "AE", True),
        ("SG", "AE", True),
        ("GB", "AE", True),
        ("", "AE", True),
        ("AE", "CN", False),
        ("US", "AE", False),
    ],
)
def test_corridors_follow_the_fta_list(o: str, b: str, hit: bool) -> None:
    w = wire(party("A", "DE", o, eid="a"), party("B", "DE", b, eid="b"), purpose="rice consignment")
    assert ("SB-CORRIDOR" in codes(one(w).findings)) is hit


def test_scope_value_floor_is_500k() -> None:
    assert "SB-SCOPE-VALUE" in codes(one(wire(DE, US, 500_000)).findings)
    assert "SB-SCOPE-VALUE" not in codes(one(wire(DE, US, "499999.99")).findings)


def test_reg_bank_split_needs_a_hub_on_both_sides() -> None:
    assert "SB-REG-BANK-SPLIT" in codes(one(wire(HK, DE)).findings, "originator")
    de_in_ch = party("Dorvin", "DE", "CH", eid="d2")
    assert "SB-REG-BANK-SPLIT" not in codes(one(wire(de_in_ch, US)).findings)
    sg_in_us = party("Senrho", "SG", "US", eid="s2")
    assert "SB-REG-BANK-SPLIT" not in codes(one(wire(sg_in_us, US)).findings)


def test_young_uses_wire_date_and_ignores_future_incorporation() -> None:
    ents = {"HK1": entity("HK1", incorporated=date(2026, 1, 1))}
    assert "SB-YOUNG" in codes(one(wire(HK, DE, when=date(2026, 12, 31)), entities=ents).findings)
    assert "SB-YOUNG" not in codes(one(wire(HK, DE, when=date(2027, 1, 1)), entities=ents).findings)
    assert "SB-YOUNG" not in codes(one(wire(HK, DE, when=date(2025, 12, 1)), entities=ents).findings)


def test_web_and_ownership_unknown_is_not_a_finding() -> None:
    ents = {
        "HK1": entity("HK1", website="", owners_disclosed=False),
        "DE1": entity("DE1", website=None, owners_disclosed=None),
    }
    r = one(wire(HK, DE), entities=ents)
    assert {"SB-NO-WEB", "SB-OPAQUE"} <= codes(r.findings, "originator")
    assert not codes(r.findings, "beneficiary") & {"SB-NO-WEB", "SB-OPAQUE"}


def test_sof_missing_only_for_multimillion_generic_purpose() -> None:
    assert "SB-SOF-MISSING" in codes(one(wire(DE, US, 1_000_000, purpose="INV 4471")).findings)
    assert "SB-SOF-MISSING" in codes(one(wire(DE, US, 3_000_000, purpose="")).findings)
    assert "SB-SOF-MISSING" not in codes(one(wire(DE, US, 999_999, purpose="")).findings)
    assert "SB-SOF-MISSING" not in codes(one(wire(DE, US, 5_000_000, purpose="copper cathode")).findings)


def test_lob_mismatch_checks_the_customer_side() -> None:
    ents = {
        "DE1": entity("DE1", line_of_business="metals trading"),
        "US1": entity("US1", line_of_business="food"),
    }
    r = one(wire(DE, US, purpose="consulting fee", customer="originator"), entities=ents)
    assert codes(r.findings, "originator") >= {"SB-LOB-MISMATCH"}
    assert "SB-LOB-MISMATCH" not in codes(r.findings, "beneficiary")
    r2 = one(wire(DE, US, purpose="copper and freight", customer="originator"), entities=ents)
    assert "SB-LOB-MISMATCH" not in codes(r2.findings)
    # Without a customer column both sides are checked.
    r3 = one(wire(DE, US, purpose="consulting fee", customer=""), entities=ents)
    assert {f.role for f in r3.findings if f.code == "SB-LOB-MISMATCH"} == {"originator", "beneficiary"}


def test_freezone_is_uae_only_except_explicit_dmcc() -> None:
    hk_fze = party("Lio FZE", "HK", "HK", eid="x1")
    assert "SB-FREEZONE" not in codes(one(wire(hk_fze, US)).findings)
    unknown_dmcc = party("Lio DMCC", "", "", eid="x2")
    assert "SB-FREEZONE" in codes(one(wire(unknown_dmcc, US)).findings)


def test_offshore_registry_from_list_or_colocation() -> None:
    addr = "Unit 3, Registry Complex, Liotal Road, Majuro"
    mh = party("Dorvin Maritime Inc", "MH", "SG", eid="MH1", address=addr)
    plain = one(wire(mh, US))
    assert "SB-OFFSHORE" in codes(plain.findings) and "SB-OFFSHORE-REGISTRY" not in codes(plain.findings)
    cfg = Config(registry_addresses=frozenset({building_key("Registry Complex, Liotal Road, Majuro")}))
    listed = one(wire(mh, US), cfg=cfg)
    assert "SB-OFFSHORE-REGISTRY" in codes(listed.findings)
    tenants = [
        party(f"Shell {i}", "VG", "SG", eid=f"VG{i}", address=f"Unit {i}, 9 Talsen Rd, Tortola")
        for i in range(5)
    ]
    res = screen([wire(t, US) for t in tenants])
    assert all("SB-OFFSHORE-REGISTRY" in codes(r.findings) for r in res.wires)
    assert all("SB-COLOCATED" in codes(r.findings) for r in res.wires)


def test_colocation_threshold() -> None:
    tenants = [
        party(f"T{i}", "AE", "AE", eid=f"T{i}", address=f"Office {i}, Tower 2, Senqua Road") for i in range(4)
    ]
    res = screen([wire(t, US) for t in tenants])
    assert not any("SB-COLOCATED" in codes(r.findings) for r in res.wires)
    res2 = screen([wire(t, US) for t in tenants], cfg=Config(colocated_min=4))
    assert all("SB-COLOCATED" in codes(r.findings) for r in res2.wires)


def test_burst_window_is_inclusive_and_bounded() -> None:
    ws = [wire(HK, DE, 1_000_000, when=date(2026, 1, d), purpose="rice") for d in (1, 15, 30)]
    res = screen(ws)
    assert all("SB-BURST" in codes(r.findings) for r in res.wires)
    ws2 = [wire(HK, DE, 1_000_000, when=date(2026, 1, 1), purpose="rice")] + [
        wire(HK, DE, 1_000_000, when=date(2026, 1, d), purpose="rice") for d in (15,)
    ]
    ws2.append(wire(HK, DE, 1_000_000, when=date(2026, 1, 31), purpose="rice"))
    assert not any("SB-BURST" in codes(r.findings) for r in screen(ws2).wires)
    small = [wire(HK, DE, 999_999, when=date(2026, 1, d), purpose="rice") for d in (1, 2, 3)]
    assert not any("SB-BURST" in codes(r.findings) for r in screen(small).wires)


def test_burst_evidence_reports_densest_window() -> None:
    ws = [wire(HK, DE, 1_000_000, when=date(2026, 1, d), purpose="rice") for d in (1, 2, 3, 4)]
    res = screen(ws)
    ev = next(f.evidence for f in res.entity_findings["HK1"] if f.code == "SB-BURST")
    assert ev.startswith("4 wires") and "$4,000,000" in ev


def test_no_opex_needs_flow_span_and_no_expense_debits() -> None:
    led = [
        LedgerEntry("HK1", date(2026, 1, 1), Decimal(2_000_000), "wire in"),
        LedgerEntry("HK1", date(2026, 4, 1), Decimal(-2_000_000), "wire out"),
        LedgerEntry("DE1", date(2026, 1, 1), Decimal(2_000_000), "wire in"),
        LedgerEntry("DE1", date(2026, 2, 1), Decimal(-50_000), "payroll"),
        LedgerEntry("DE1", date(2026, 4, 1), Decimal(-2_000_000), "wire out"),
        LedgerEntry("US1", date(2026, 1, 1), Decimal(2_000_000), "wire in"),
        LedgerEntry("US1", date(2026, 1, 20), Decimal(-2_000_000), "wire out"),
    ]
    res = screen([wire(HK, DE), wire(US, DE)], ledger=led)
    assert "SB-NO-OPEX" in codes(res.entity_findings["HK1"])
    assert "SB-NO-OPEX" not in codes(res.entity_findings.get("DE1", []))
    assert "SB-NO-OPEX" not in codes(res.entity_findings.get("US1", []))


def test_opex_credit_does_not_count_as_expense() -> None:
    led = [
        LedgerEntry("HK1", date(2026, 1, 1), Decimal(2_000_000), "wire in"),
        LedgerEntry("HK1", date(2026, 3, 1), Decimal(100), "payroll"),
        LedgerEntry("HK1", date(2026, 4, 1), Decimal(-2_000_000), "wire out"),
    ]
    assert "SB-NO-OPEX" in codes(screen([wire(HK, DE)], ledger=led).entity_findings["HK1"])


def test_banque_misr_uae_only() -> None:
    bm = party("Tusket", "AE", "AE", eid="b1", bank_name="Banque Misr UAE")
    r = one(wire(DE, bm, purpose="rice"))
    assert "SB-BANK-311-PROPOSED" in codes(r.findings)
    assert r.disposition == "review"
    assert "proposed" in next(f.evidence for f in r.findings if f.code == "SB-BANK-311-PROPOSED")
    eg = party("Tusket", "EG", "EG", eid="b2", bank_name="Banque Misr")
    assert "SB-BANK-311-PROPOSED" not in codes(one(wire(DE, eg)).findings)


def test_run_findings_say_what_did_not_run() -> None:
    res = screen([wire(DE, US, customer="")])
    text = " ".join(f.evidence for f in res.run_findings)
    assert "no entities file" in text and "no ledger" in text and "no customer column" in text
    res2 = screen([wire(DE, US)], entities={"DE1": entity("DE1")}, ledger=[])
    assert res2.run_findings == []


def f(code: str) -> Finding:
    return Finding(code, "wire", "x", "")


def test_decide_rules() -> None:
    cfg = Config()
    assert decide([], cfg)[0] == "clear"
    assert decide([f("SB-HUB-REG")], cfg)[0] == "clear"
    assert decide([f("SB-CORRIDOR"), f("SB-REG-BANK-SPLIT")], cfg)[0] == "note"
    assert decide([f("SB-FREEZONE")], cfg)[0] == "watch"
    assert decide([f("SB-OPAQUE"), f("SB-SOF-MISSING")], cfg)[0] == "review"
    assert decide([f("SB-OPAQUE"), f("SB-YOUNG")], cfg)[0] == "watch"
    # Three families but every finding low: still watch.
    assert decide([f("SB-CORRIDOR"), f("SB-FREEZONE"), f("SB-NET-SHARED-ADDR")], cfg)[0] == "watch"
    assert decide([f("SB-CORRIDOR"), f("SB-OPAQUE"), f("SB-NET-SHARED-ADDR")], cfg)[0] == "review"
    assert (
        decide([f("SB-CORRIDOR"), f("SB-OPAQUE"), f("SB-NET-SHARED-ADDR")], Config(min_families=4))[0]
        == "watch"
    )
    assert decide([f("SB-BANK-311-PROPOSED")], cfg)[0] == "review"


def test_config_validation() -> None:
    with pytest.raises(ValueError):
        Config(min_families=1)
    with pytest.raises(ValueError):
        Config(burst_days=0)


def test_network_findings_need_a_flagged_partner_and_a_significant_overlap() -> None:
    # Two shells share three small suppliers that nobody else uses; a busy importer shares two
    # common suppliers by chance.
    shells = [party(f"S{i}", "HK", "CN", eid=f"S{i}") for i in range(2)]
    sup = [party(f"P{i}", "DE", "DE", eid=f"P{i}") for i in range(3)]
    ents = {s.entity_id: entity(s.entity_id, owners_disclosed=False) for s in shells}
    ws = [wire(s, p, purpose="rice") for s in shells for p in sup]
    others = [party(f"O{i}", "US", "US", eid=f"O{i}") for i in range(40)]
    for i, o in enumerate(others):
        ws.append(wire(o, others[(i + 1) % 40], purpose="rice"))
        ws.append(wire(o, others[(i + 7) % 40], purpose="rice"))
    res = screen(ws, entities=ents)
    s0 = codes(res.entity_findings["S0"])
    assert "SB-NET-SHARED-CPTY" in s0
    assert not any(
        "SB-NET-SHARED-CPTY" in codes(v) for k, v in res.entity_findings.items() if k.startswith("O")
    )
