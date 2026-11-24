"""Attribution-lag development: how much activity has not been tied to a network yet.

FinCEN's FTA (p. 7) notes "an attribution lag between the time a transaction occurs and when
FinCEN or FinCEN sources attribute it to Iran", and estimates the missing part with "concepts from
actuarial loss development methods". Footnote 7 points to Friedland's chapter on the development
technique, also called chain ladder:

    Friedland, Estimating Unpaid Claims Using Basic Techniques, Chapter 7, Development Technique.
    https://www.actexmadriver.com/Assets/ClientDocs/prod_preview/A105RC.pdf

An investigations team has the same problem with its own case data: transactions from recent months
are under-counted because nobody has linked them yet. This module applies that chain-ladder method
to the team's own cases. The standard errors are from Mack (1993), which is this tool's choice for
error ranges, not a method FinCEN cited:

    Mack, T. (1993). Distribution-free calculation of the standard error of chain ladder reserve
    estimates. ASTIN Bulletin 23(2), 213-225.

Rows are origin periods (when the transactions happened), columns are development lags (how many
periods later they were attributed), cells are cumulative attributed value. This is our own use of
the method on a team's case data; it is not FinCEN's model, which the FTA does not publish.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Literal

Period = Literal["month", "quarter"]


@dataclass(frozen=True)
class Case:
    txn_date: date
    attributed_date: date
    amount_usd: Decimal


@dataclass
class DevelopmentResult:
    origins: list[str]
    latest: list[float]
    ultimate: list[float]
    unattributed: list[float]
    se: list[float]
    factors: list[float]
    sigma2: list[float]
    total_latest: float
    total_unattributed: float
    total_se: float
    notes: list[str]

    @property
    def total_cv(self) -> float:
        return self.total_se / self.total_unattributed if self.total_unattributed else 0.0


def period_index(d: date, period: Period) -> int:
    if period == "month":
        return d.year * 12 + d.month - 1
    return d.year * 4 + (d.month - 1) // 3


def period_label(idx: int, period: Period) -> str:
    if period == "month":
        return f"{idx // 12:04d}-{idx % 12 + 1:02d}"
    return f"{idx // 4:04d}-Q{idx % 4 + 1}"


def triangle_from_cases(
    cases: Iterable[Case], period: Period = "month", as_of: date | None = None
) -> tuple[list[str], list[list[float]], int]:
    """Cumulative triangle as of ``as_of`` (default: the latest attribution date).

    Returns origin labels, the triangle (row i has ``n - i`` cells) and the number of cases left
    out because they were attributed after ``as_of``.
    """
    items = list(cases)
    if not items:
        raise ValueError("no cases")
    for c in items:
        if c.attributed_date < c.txn_date:
            raise ValueError(f"case attributed {c.attributed_date} before its transaction {c.txn_date}")
    as_of = as_of or max(c.attributed_date for c in items)
    first = min(period_index(c.txn_date, period) for c in items)
    last = period_index(as_of, period)
    if last < first:
        raise ValueError("as_of is before the first transaction")
    n = last - first + 1
    inc: dict[tuple[int, int], float] = defaultdict(float)
    skipped = 0
    for c in items:
        if c.attributed_date > as_of:
            skipped += 1
            continue
        i = period_index(c.txn_date, period) - first
        k = period_index(c.attributed_date, period) - period_index(c.txn_date, period)
        inc[(i, k)] += float(c.amount_usd)
    tri: list[list[float]] = []
    for i in range(n):
        row: list[float] = []
        run = 0.0
        for k in range(n - i):
            run += inc.get((i, k), 0.0)
            row.append(run)
        tri.append(row)
    return [period_label(first + i, period) for i in range(n)], tri, skipped


def chain_ladder(
    triangle: Sequence[Sequence[float]], origins: Sequence[str] | None = None
) -> DevelopmentResult:
    """Chain-ladder ultimates with Mack standard errors.

    ``triangle[i]`` holds the cumulative values for origin ``i`` at lags ``0 .. n-1-i``.
    """
    n = len(triangle)
    if n < 2:
        raise ValueError("need at least two origin periods")
    for i, row in enumerate(triangle):
        if len(row) != n - i:
            raise ValueError(f"row {i} has {len(row)} cells, expected {n - i}")
        if any(v < 0 or not math.isfinite(v) for v in row):
            raise ValueError(f"row {i} has a negative or non-finite value")
    c = [list(map(float, row)) for row in triangle]
    notes: list[str] = []

    # Volume-weighted age-to-age factors and column sums S_k over the rows that have lag k+1.
    f: list[float] = []
    s: list[float] = []
    for k in range(n - 1):
        rows = range(n - 1 - k)
        num = sum(c[i][k + 1] for i in rows)
        den = sum(c[i][k] for i in rows)
        s.append(den)
        if den == 0:
            f.append(1.0)
            notes.append(f"lag {k}: nothing attributed yet in any older origin; factor set to 1")
        else:
            f.append(num / den)

    # Mack's sigma^2_k; the last one is extrapolated as in Mack (1993), section 3.
    sigma2: list[float] = []
    for k in range(n - 1):
        used = [i for i in range(n - 1 - k) if c[i][k] > 0]
        if len(used) >= 2:
            ss = sum(c[i][k] * (c[i][k + 1] / c[i][k] - f[k]) ** 2 for i in used)
            sigma2.append(ss / (len(used) - 1))
        else:
            sigma2.append(math.nan)
    for k in range(n - 1):
        if math.isnan(sigma2[k]):
            if (
                k >= 2
                and not math.isnan(sigma2[k - 1])
                and not math.isnan(sigma2[k - 2])
                and sigma2[k - 2] > 0
            ):
                a, b = sigma2[k - 1], sigma2[k - 2]
                sigma2[k] = min(a * a / b, min(a, b))
            else:
                sigma2[k] = 0.0
                if n > 2:
                    notes.append(f"lag {k}: too few points to estimate variance; standard error understated")

    # Projected cumulative values.
    full: list[list[float]] = []
    for i in range(n):
        row = list(c[i])
        for k in range(n - 1 - i, n - 1):
            row.append(row[k] * f[k])
        full.append(row)

    latest = [c[i][n - 1 - i] for i in range(n)]
    ultimate = [full[i][n - 1] for i in range(n)]
    reserve = [ultimate[i] - latest[i] for i in range(n)]

    def term_sum(i: int, total: bool) -> float:
        acc = 0.0
        for k in range(n - 1 - i, n - 1):
            if f[k] == 0 or s[k] == 0:
                continue
            base = sigma2[k] / (f[k] ** 2)
            if total:
                acc += 2 * base / s[k]
            elif full[i][k] > 0:
                acc += base * (1 / full[i][k] + 1 / s[k])
        return acc

    mse = [ultimate[i] ** 2 * term_sum(i, False) for i in range(n)]
    se = [math.sqrt(m) for m in mse]
    total_mse = 0.0
    for i in range(n):
        younger = sum(ultimate[j] for j in range(i + 1, n))
        total_mse += mse[i] + ultimate[i] * younger * term_sum(i, True)

    return DevelopmentResult(
        origins=list(origins) if origins is not None else [str(i) for i in range(n)],
        latest=latest,
        ultimate=ultimate,
        unattributed=reserve,
        se=se,
        factors=f,
        sigma2=sigma2,
        total_latest=sum(latest),
        total_unattributed=sum(reserve),
        total_se=math.sqrt(total_mse),
        notes=notes,
    )
