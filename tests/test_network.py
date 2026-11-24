from __future__ import annotations

import itertools
import math
from decimal import Decimal

from hypothesis import given
from hypothesis import strategies as st

from shadowbank.network import build_network, neighbours, overlap_p, shared_counterparties, significant_pairs

from .conftest import party, wire


def exact_tail(n: int, da: int, db: int, k: int) -> float:
    total = sum(math.comb(da, x) * math.comb(n - da, db - x) for x in range(k, min(da, db) + 1))
    return total / math.comb(n, db)


@given(
    st.integers(1, 60).flatmap(
        lambda n: st.tuples(st.just(n), st.integers(1, n), st.integers(1, n), st.integers(0, n))
    )
)
def test_overlap_p_matches_exact_hypergeometric(t: tuple[int, int, int, int]) -> None:
    n, da, db, k = t
    want = 1.0 if k <= 0 else (0.0 if k > min(da, db) else exact_tail(n, da, db, k))
    assert math.isclose(overlap_p(n, da, db, k), want, rel_tol=1e-9, abs_tol=1e-12)


def test_overlap_p_is_monotone_in_k() -> None:
    ps = [overlap_p(500, 20, 20, k) for k in range(0, 21)]
    assert all(a >= b for a, b in itertools.pairwise(ps))
    assert ps[0] == 1.0 and ps[-1] > 0


def test_hubs_are_skipped_and_pairs_are_sorted() -> None:
    hub = party("Hub", "DE", "DE", eid="H")
    ws = [wire(party(f"x{i}", "DE", "DE", eid=f"x{i}"), hub) for i in range(5)]
    pairs, hubs = shared_counterparties(neighbours(ws), max_degree=4)
    assert hubs == {"H"} and pairs == {}
    pairs2, hubs2 = shared_counterparties(neighbours(ws), max_degree=5)
    assert hubs2 == set() and len(pairs2) == 10
    assert all(a < b for a, b in pairs2)


def test_self_transfers_are_not_edges() -> None:
    a = party("A", "DE", "DE", eid="A")
    assert neighbours([wire(a, a)]) == {}


def test_significant_pairs_filters_chance_overlap() -> None:
    adj = {"a": {"x", "y"}, "b": {"x", "y"}, "x": {"a", "b"}, "y": {"a", "b"}}
    pairs, _ = significant_pairs(adj, 50, 2, 0.5)
    assert ("a", "b") in pairs
    pairs2, _ = significant_pairs(adj, 50, 2, 1e-9)
    assert pairs2 == {}


def test_build_network_links_by_transfer_building_and_counterparties() -> None:
    a = party("A", "HK", "CN", eid="A", address="Office 1, Tower 9, Senrho Road")
    b = party("B", "AE", "AE", eid="B", address="Office 2, Tower 9, Senrho Road")
    c = party("C", "AE", "AE", eid="C")
    d = party("D", "AE", "AE", eid="D")
    e = party("E", "US", "US", eid="E")
    ws = [wire(a, e, 1_000_000, wid="1"), wire(c, d, 2_000_000, wid="2"), wire(e, b, 5, wid="3")]
    buildings = {"A": "TWR 9 SENRHO RD", "B": "TWR 9 SENRHO RD"}
    cl = build_network(ws, {"A", "B", "C", "D"}, buildings, {"2"})
    assert [c_.members for c_ in cl] == [["C", "D"], ["A", "B"]]
    assert (
        cl[0].links == {"transfer": 1} and cl[0].value_usd == Decimal(2_000_000) and cl[0].review_wires == 1
    )
    assert cl[1].links == {"building": 1} and cl[1].shared_buildings == ["TWR 9 SENRHO RD"]
    assert cl[1].wires == 2
    assert [c_.id for c_ in cl] == ["C001", "C002"]


def test_singletons_are_dropped() -> None:
    a = party("A", "HK", "CN", eid="A")
    e = party("E", "US", "US", eid="E")
    assert build_network([wire(a, e)], {"A"}, {}, set()) == []
