"""Back-test the checks against outcomes your investigators already recorded.

FinCEN's dataset is wires that institutions reported and FinCEN then corroborated (FTA p. 4).
A team can run the same loop on its own history: screen past wires, join the result to the
case outcome (escalated and confirmed, or closed as explained), and see what each code is worth.

Labels are 1 (confirmed concern) or 0 (closed). Unlabelled wires are left out. Precision is given
with a Wilson score interval because most codes fire on few wires and a bare ratio misleads.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from .screen import Config, WireResult, decide


def wilson(k: int, n: int, z: float = 1.959964) -> tuple[float, float]:
    """Wilson score interval for k successes in n trials."""
    if n == 0:
        return (0.0, 1.0)
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (max(0.0, centre - half), min(1.0, centre + half))


@dataclass(frozen=True)
class CodeStat:
    code: str
    hits: int
    true_hits: int
    precision: float
    low: float
    high: float
    recall: float
    lift: float


@dataclass(frozen=True)
class SweepRow:
    min_families: int
    review: int
    true_review: int
    precision: float
    recall: float


@dataclass(frozen=True)
class Calibration:
    labelled: int
    positives: int
    base_rate: float
    codes: list[CodeStat]
    sweep: list[SweepRow]


def calibrate(
    results: Sequence[WireResult], labels: Mapping[str, int], cfg: Config | None = None
) -> Calibration:
    cfg = cfg or Config()
    rows = [r for r in results if r.wire.id in labels]
    pos = sum(1 for r in rows if labels[r.wire.id] == 1)
    n = len(rows)
    base = pos / n if n else 0.0
    by_code: dict[str, list[int]] = {}
    for r in rows:
        y = labels[r.wire.id]
        for code in {f.code for f in r.findings}:
            by_code.setdefault(code, []).append(y)
    stats: list[CodeStat] = []
    for code, ys in by_code.items():
        k, m = sum(ys), len(ys)
        lo, hi = wilson(k, m)
        prec = k / m
        stats.append(
            CodeStat(
                code=code,
                hits=m,
                true_hits=k,
                precision=prec,
                low=lo,
                high=hi,
                recall=k / pos if pos else 0.0,
                lift=prec / base if base else 0.0,
            )
        )
    stats.sort(key=lambda s: (-s.low, s.code))
    sweep: list[SweepRow] = []
    for mf in range(2, 6):
        c2 = replace(cfg, min_families=mf)
        flagged = [r for r in rows if decide(r.findings, c2)[0] == "review"]
        tp = sum(labels[r.wire.id] for r in flagged)
        sweep.append(
            SweepRow(
                min_families=mf,
                review=len(flagged),
                true_review=tp,
                precision=tp / len(flagged) if flagged else 0.0,
                recall=tp / pos if pos else 0.0,
            )
        )
    return Calibration(labelled=n, positives=pos, base_rate=base, codes=stats, sweep=sweep)
