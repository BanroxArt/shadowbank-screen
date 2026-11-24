from __future__ import annotations

import math
from datetime import date
from decimal import Decimal

import pytest
from hypothesis import given
from hypothesis import strategies as st

from shadowbank.develop import Case, chain_ladder, period_index, period_label, triangle_from_cases

# Taylor and Ashe (1983) cumulative triangle, the data set used in Mack (1993).
TAYLOR_ASHE = [
    [357848, 1124788, 1735330, 2218270, 2745596, 3319994, 3466336, 3606286, 3833515, 3901463],
    [352118, 1236139, 2170033, 3353322, 3799067, 4120063, 4647867, 4914039, 5339085],
    [290507, 1292306, 2218525, 3235179, 3985995, 4132918, 4628910, 4909315],
    [310608, 1418858, 2195047, 3757447, 4029929, 4381982, 4588268],
    [443160, 1136350, 2128333, 2897821, 3402672, 3873311],
    [396132, 1333217, 2180715, 2985752, 3691712],
    [440832, 1288463, 2419861, 3483130],
    [359480, 1421128, 2864498],
    [376686, 1363294],
    [344014],
]


def test_reproduces_mack_1993_on_taylor_ashe() -> None:
    r = chain_ladder(TAYLOR_ASHE)
    assert round(r.total_unattributed) == 18_680_856
    assert round(r.total_se) == 2_447_095
    assert [round(x) for x in r.unattributed] == [
        0,
        94_634,
        469_511,
        709_638,
        984_889,
        1_419_459,
        2_177_641,
        3_920_301,
        4_278_972,
        4_625_811,
    ]
    assert [round(x) for x in r.se[1:]] == [
        75_535,
        121_699,
        133_549,
        261_406,
        411_010,
        558_317,
        875_328,
        971_258,
        1_363_155,
    ]
    assert round(r.factors[0], 4) == 3.4906


def test_shape_validation() -> None:
    with pytest.raises(ValueError):
        chain_ladder([[1.0]])
    with pytest.raises(ValueError):
        chain_ladder([[1.0, 2.0], [1.0, 2.0]])
    with pytest.raises(ValueError):
        chain_ladder([[1.0, -2.0], [1.0]])


def test_zero_column_sets_factor_to_one_with_note() -> None:
    r = chain_ladder([[0.0, 0.0, 5.0], [0.0, 0.0], [3.0]])
    assert r.factors[0] == 1.0
    assert any("factor set to 1" in n for n in r.notes)


def test_periods() -> None:
    assert period_label(period_index(date(2026, 8, 31), "month"), "month") == "2026-08"
    assert period_label(period_index(date(2026, 8, 31), "quarter"), "quarter") == "2026-Q3"
    assert period_index(date(2026, 1, 1), "month") - period_index(date(2025, 12, 31), "month") == 1


def test_triangle_from_cases_and_as_of() -> None:
    cases = [
        Case(date(2026, 1, 5), date(2026, 1, 20), Decimal(10)),
        Case(date(2026, 1, 5), date(2026, 3, 2), Decimal(5)),
        Case(date(2026, 2, 5), date(2026, 2, 6), Decimal(7)),
        Case(date(2026, 3, 1), date(2026, 3, 31), Decimal(1)),
        Case(date(2026, 3, 1), date(2026, 4, 1), Decimal(100)),
    ]
    origins, tri, skipped = triangle_from_cases(cases, "month", date(2026, 3, 31))
    assert origins == ["2026-01", "2026-02", "2026-03"]
    assert tri == [[10.0, 10.0, 15.0], [7.0, 7.0], [1.0]]
    assert skipped == 1
    with pytest.raises(ValueError):
        triangle_from_cases([Case(date(2026, 2, 1), date(2026, 1, 1), Decimal(1))])
    with pytest.raises(ValueError):
        triangle_from_cases([])


@st.composite
def triangles(draw: st.DrawFn) -> list[list[float]]:
    n = draw(st.integers(2, 8))
    rows = []
    for i in range(n):
        v = draw(st.floats(1, 1e6))
        row = [v]
        for _ in range(n - i - 1):
            v += draw(st.floats(0, 1e6))
            row.append(v)
        rows.append(row)
    return rows


@given(triangles())
def test_monotone_triangles_give_nonnegative_finite_results(tri: list[list[float]]) -> None:
    r = chain_ladder(tri)
    assert all(f >= 1 for f in r.factors)
    assert all(x >= -1e-6 for x in r.unattributed)
    assert r.unattributed[0] == 0
    assert all(math.isfinite(x) and x >= 0 for x in r.se)
    assert math.isfinite(r.total_se)
    assert math.isclose(sum(r.unattributed), r.total_unattributed, rel_tol=1e-9, abs_tol=1e-6)
    # The total standard error is at least the largest single-origin one.
    assert r.total_se + 1e-6 >= max(r.se)
