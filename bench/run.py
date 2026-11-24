"""Time the screen, the network build and the development model on scaled synthetic data.

PYTHONPATH=src python bench/run.py [scale]
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import time
from datetime import date
from decimal import Decimal
from pathlib import Path

from shadowbank.develop import Case, chain_ladder, triangle_from_cases
from shadowbank.model import iter_rows, read_entities, read_ledger, read_lines, read_wires
from shadowbank.network import build_network
from shadowbank.normalize import building_key
from shadowbank.screen import Config, screen

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    scale = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp)
        subprocess.run(
            [sys.executable, str(ROOT / "examples" / "make_examples.py"), tmp, "--scale", str(scale)],
            check=True,
        )
        t0 = time.perf_counter()
        wires = read_wires(out / "wires.csv")
        ents = read_entities(out / "entities.csv")
        ledger = read_ledger(out / "ledger.csv")
        reg = frozenset(building_key(x) for x in read_lines(out / "registry.txt"))
        t1 = time.perf_counter()
        res = screen(wires, ents, ledger, Config(registry_addresses=reg))
        t2 = time.perf_counter()
        review = {r.wire.id for r in res.wires if r.disposition == "review"}
        clusters = build_network(wires, res.flagged, res.buildings, review)
        t3 = time.perf_counter()
        cases = [
            Case(
                date.fromisoformat(r["txn_date"]),
                date.fromisoformat(r["attributed_date"]),
                Decimal(r["amount_usd"]),
            )
            for _, r in iter_rows(out / "cases.csv")
        ]
        origins, tri, _ = triangle_from_cases(cases)
        chain_ladder(tri, origins)
        t4 = time.perf_counter()
    print(f"{len(wires):,} wires, {len(ents):,} entities, {len(ledger):,} ledger rows, {len(cases):,} cases")
    print(f"read     {t1 - t0:7.2f} s")
    per = (t2 - t1) / len(wires) * 1e6
    print(f"screen   {t2 - t1:7.2f} s  ({per:.1f} us a wire), {len(review):,} for review")
    print(f"network  {t3 - t2:7.2f} s  {len(clusters)} clusters")
    print(f"develop  {t4 - t3:7.2f} s")


if __name__ == "__main__":
    main()
