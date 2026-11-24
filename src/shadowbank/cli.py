"""Command line.

    shadowbank screen wires.csv [--entities E] [--ledger L] [--registry R] [--format text|json|csv]
    shadowbank network wires.csv [--entities E] [--ledger L] [--json]
    shadowbank develop cases.csv [--period month|quarter] [--as-of DATE] [--json]
    shadowbank calibrate wires.csv labels.csv [--entities E] [--ledger L]
    shadowbank codes

Exit codes: 0 nothing for review, 1 at least one wire for review (screen only), 2 bad input.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from pathlib import Path

from .calibrate import calibrate
from .develop import Case, chain_ladder, triangle_from_cases
from .model import InputError, iter_rows, read_entities, read_ledger, read_lines, read_wires
from .network import Cluster, build_network
from .normalize import building_key
from .report import (
    calibration_text,
    cluster_dict,
    cluster_text,
    codes_text,
    develop_json,
    develop_text,
    screen_csv,
    screen_json,
    screen_text,
)
from .screen import Config, ScreenResult, screen


def _common(p: argparse.ArgumentParser) -> None:
    p.add_argument("wires", type=Path)
    p.add_argument("--entities", type=Path, help="entity profiles (CSV or JSONL)")
    p.add_argument("--ledger", type=Path, help="account postings with a category (CSV or JSONL)")
    p.add_argument("--registry", type=Path, help="registry or registered-agent addresses, one per line")
    p.add_argument("--young-days", type=int, default=365)
    p.add_argument("--colocated-min", type=int, default=5)
    p.add_argument("--min-families", type=int, default=3)
    p.add_argument("--shared-min", type=int, default=2)
    p.add_argument("--shared-p", type=float, default=0.001, help="max chance overlap p-value")
    p.add_argument("--max-degree", type=int, default=50, help="skip counterparties with more neighbours")


def _run(a: argparse.Namespace) -> tuple[ScreenResult, Config]:
    registry = frozenset(building_key(x) for x in read_lines(a.registry)) if a.registry else frozenset()
    cfg = Config(
        young_days=a.young_days,
        colocated_min=a.colocated_min,
        min_families=a.min_families,
        shared_min=a.shared_min,
        max_counterparty_degree=a.max_degree,
        shared_p=a.shared_p,
        registry_addresses=registry,
    )
    wires = read_wires(a.wires)
    entities = read_entities(a.entities) if a.entities else None
    ledger = read_ledger(a.ledger) if a.ledger else None
    return screen(wires, entities, ledger, cfg), cfg


def _clusters(result: ScreenResult, cfg: Config) -> list[Cluster]:
    return build_network(
        [r.wire for r in result.wires],
        result.flagged,
        result.buildings,
        {r.wire.id for r in result.wires if r.disposition == "review"},
        cfg.shared_min,
        cfg.max_counterparty_degree,
        cfg.shared_p,
    )


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="shadowbank",
        description="Screen wires against FinCEN's Nov 2026 Iranian shadow banking findings. "
        "Engineering checklist, not legal advice.",
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("screen", help="findings and a disposition for each wire")
    _common(s)
    s.add_argument("--format", choices=["text", "json", "csv"], default="text")
    s.add_argument("--show", default="review,watch", help="dispositions to list in text output")
    n = sub.add_parser("network", help="clusters of flagged parties")
    _common(n)
    n.add_argument("--json", action="store_true")
    d = sub.add_parser("develop", help="chain-ladder estimate of value not yet attributed")
    d.add_argument("cases", type=Path, help="txn_date, attributed_date, amount_usd")
    d.add_argument("--period", choices=["month", "quarter"], default="month")
    d.add_argument("--as-of", type=date.fromisoformat)
    d.add_argument("--json", action="store_true")
    c = sub.add_parser("calibrate", help="precision and recall of each code against past outcomes")
    _common(c)
    c.add_argument("labels", type=Path, help="wire_id, label (1 confirmed, 0 closed)")
    sub.add_parser("codes", help="list finding codes and their sources")
    a = ap.parse_args(argv)

    try:
        if a.cmd == "codes":
            sys.stdout.write(codes_text())
            return 0
        if a.cmd == "develop":
            cases = [
                Case(
                    date.fromisoformat(r["txn_date"][:10]),
                    date.fromisoformat(r["attributed_date"][:10]),
                    Decimal(r["amount_usd"].replace(",", "")),
                )
                for _, r in iter_rows(a.cases)
            ]
            origins, tri, skipped = triangle_from_cases(cases, a.period, a.as_of)
            res = chain_ladder(tri, origins)
            if skipped:
                res.notes.append(f"{skipped} cases attributed after the as-of date were left out")
            sys.stdout.write(develop_json(res) if a.json else develop_text(res))
            return 0
        result, cfg = _run(a)
        review_ids = {r.wire.id for r in result.wires if r.disposition == "review"}
        if a.cmd == "screen":
            if a.format == "json":
                clusters = _clusters(result, cfg)
                sys.stdout.write(screen_json(result, clusters))
            elif a.format == "csv":
                sys.stdout.write(screen_csv(result))
            else:
                sys.stdout.write(screen_text(result, set(a.show.split(","))))
            return 1 if review_ids else 0
        if a.cmd == "network":
            clusters = _clusters(result, cfg)
            if a.json:
                sys.stdout.write(json.dumps([cluster_dict(x) for x in clusters], indent=2) + "\n")
            else:
                out = [f"{len(clusters)} clusters of flagged parties"]
                for x in clusters:
                    out.extend(cluster_text(x))
                sys.stdout.write("\n".join(out) + "\n")
            return 0
        if a.cmd == "calibrate":
            labels: dict[str, int] = {}
            for i, r in iter_rows(a.labels):
                v = r.get("label", "").strip()
                if v not in {"0", "1"}:
                    raise InputError(f"{a.labels.name}:{i}: label must be 0 or 1")
                labels[r.get("wire_id", "").strip()] = int(v)
            sys.stdout.write(calibration_text(calibrate(result.wires, labels, cfg)))
            return 0
    except (InputError, ValueError, KeyError, OSError) as exc:
        msg = f"missing column {exc}" if isinstance(exc, KeyError) else str(exc)
        print(f"shadowbank: {msg}", file=sys.stderr)
        return 2
    return 2
