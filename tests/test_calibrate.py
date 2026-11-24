from __future__ import annotations

import math

from shadowbank.calibrate import calibrate, wilson
from shadowbank.screen import screen

from .conftest import entity, party, wire


def test_wilson_known_values() -> None:
    lo, hi = wilson(0, 10)
    assert lo == 0.0 and math.isclose(hi, 0.2775, abs_tol=1e-4)
    lo, hi = wilson(5, 10)
    assert math.isclose(lo, 0.2366, abs_tol=1e-4) and math.isclose(hi, 0.7634, abs_tol=1e-4)
    assert wilson(0, 0) == (0.0, 1.0)


def test_calibrate_counts_and_sweep() -> None:
    hk = party("Varnel", "HK", "CN", eid="HK1")
    de = party("Dorvin", "DE", "DE", eid="DE1")
    us = party("Qualio", "US", "US", eid="US1")
    ents = {"HK1": entity("HK1", owners_disclosed=False)}
    ws = [wire(hk, de, 2_000_000, purpose="", wid=f"b{i}") for i in range(3)]
    ws += [wire(de, us, 100_000, purpose="rice", wid=f"g{i}") for i in range(7)]
    res = screen(ws, entities=ents)
    labels = {w.id: (1 if w.id.startswith("b") else 0) for w in ws}
    labels.pop("g6")
    c = calibrate(res.wires, labels)
    assert c.labelled == 9 and c.positives == 3
    opaque = next(s for s in c.codes if s.code == "SB-OPAQUE")
    assert (opaque.hits, opaque.true_hits, opaque.recall) == (3, 3, 1.0)
    assert [r.min_families for r in c.sweep] == [2, 3, 4, 5]
    assert c.sweep[0].true_review == 3 and c.sweep[0].precision == 1.0
