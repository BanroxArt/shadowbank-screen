"""Who trades with whom, and which flagged parties belong together.

FinCEN found that potential Iran-linked companies "frequently appeared in the same financial
networks ... with many of the same counterparties" (FTA p. 3). Two signals come out of the wire
data alone:

- shared counterparties: two parties that both pay or are paid by the same set of companies;
- shared buildings: parties whose addresses reduce to the same building key.

A shared counterparty or two means little in a dense book: two busy importers will share
suppliers by chance. So an overlap only counts when it is unlikely under random pairing, measured
by the hypergeometric tail: with ``n`` parties in the data and degrees ``da`` and ``db``, the
probability that two independent parties share ``k`` or more counterparties. The default cut is
0.001.

Counterparties with very many neighbours (a large trading house, a freight forwarder that every
importer uses) carry little information and make the pair count quadratic, so any counterparty
with more than ``max_degree`` neighbours is left out of the overlap count and reported as a hub.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from decimal import Decimal

from .model import Wire


def neighbours(wires: Iterable[Wire]) -> dict[str, set[str]]:
    adj: dict[str, set[str]] = defaultdict(set)
    for w in wires:
        a, b = w.originator.entity_id, w.beneficiary.entity_id
        if a and b and a != b:
            adj[a].add(b)
            adj[b].add(a)
    return dict(adj)


def shared_counterparties(
    adj: Mapping[str, set[str]], max_degree: int
) -> tuple[dict[tuple[str, str], set[str]], set[str]]:
    """Pairs of parties (sorted) and the counterparties they share, plus the skipped hubs.

    Cost is the sum over counterparties of degree squared, which ``max_degree`` bounds.
    """
    pairs: dict[tuple[str, str], set[str]] = defaultdict(set)
    hubs: set[str] = set()
    for cpty, nbrs in adj.items():
        if len(nbrs) > max_degree:
            hubs.add(cpty)
            continue
        ordered = sorted(nbrs)
        for i, a in enumerate(ordered):
            for b in ordered[i + 1 :]:
                pairs[(a, b)].add(cpty)
    return dict(pairs), hubs


def overlap_p(n: int, da: int, db: int, k: int) -> float:
    """P(X >= k) for X ~ Hypergeometric(population n, da marked, db drawn).

    The chance that a party with ``db`` counterparties shares at least ``k`` of them with a party
    that has ``da``, if ``db`` were drawn at random from ``n`` parties.
    """
    if k <= 0:
        return 1.0
    if n <= 0 or da <= 0 or db <= 0 or k > min(da, db):
        return 0.0
    da, db = min(da, n), min(db, n)

    def lcomb(a: int, b: int) -> float:
        return math.lgamma(a + 1) - math.lgamma(b + 1) - math.lgamma(a - b + 1)

    denom = lcomb(n, db)
    total = 0.0
    for x in range(k, min(da, db) + 1):
        if db - x > n - da:
            continue
        total += math.exp(lcomb(da, x) + lcomb(n - da, db - x) - denom)
    return min(1.0, total)


def significant_pairs(
    adj: Mapping[str, set[str]], max_degree: int, shared_min: int, p_max: float
) -> tuple[dict[tuple[str, str], tuple[int, float]], set[str]]:
    """Pairs whose counterparty overlap is at least ``shared_min`` and has p at most ``p_max``."""
    pairs, hubs = shared_counterparties(adj, max_degree)
    n = len(adj)
    out: dict[tuple[str, str], tuple[int, float]] = {}
    for (a, b), shared in pairs.items():
        k = len(shared)
        if k < shared_min:
            continue
        p = overlap_p(n, len(adj[a]), len(adj[b]), k)
        if p <= p_max:
            out[(a, b)] = (k, p)
    return out, hubs


class _UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, x: str) -> str:
        self.parent.setdefault(x, x)
        root = x
        while self.parent[root] != root:
            root = self.parent[root]
        while self.parent[x] != root:
            self.parent[x], x = root, self.parent[x]
        return root

    def union(self, a: str, b: str) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            if ra < rb:
                self.parent[rb] = ra
            else:
                self.parent[ra] = rb


@dataclass
class Cluster:
    id: str
    members: list[str]
    links: dict[str, int] = field(default_factory=dict)
    wires: int = 0
    value_usd: Decimal = Decimal(0)
    review_wires: int = 0
    shared_buildings: list[str] = field(default_factory=list)


def build_network(
    wires: list[Wire],
    flagged: set[str],
    buildings: Mapping[str, str],
    review_ids: set[str],
    shared_min: int = 2,
    max_degree: int = 50,
    p_max: float = 0.001,
) -> list[Cluster]:
    """Group flagged parties that pay each other, share a building or share counterparties.

    ``buildings`` maps entity id to building key. Only flagged parties become cluster members;
    unflagged counterparties are what links them, not part of the result. Clusters with one
    member are dropped. Sorted by value, largest first.
    """
    uf = _UnionFind()
    link_kind: dict[tuple[str, str], set[str]] = defaultdict(set)

    def link(a: str, b: str, kind: str) -> None:
        key = (a, b) if a < b else (b, a)
        link_kind[key].add(kind)
        uf.union(a, b)

    for w in wires:
        a, b = w.originator.entity_id, w.beneficiary.entity_id
        if a in flagged and b in flagged and a != b:
            link(a, b, "transfer")

    by_building: dict[str, list[str]] = defaultdict(list)
    for eid in sorted(flagged):
        key = buildings.get(eid, "")
        if key:
            by_building[key].append(eid)
    for members in by_building.values():
        for other in members[1:]:
            link(members[0], other, "building")

    pairs, _ = significant_pairs(neighbours(wires), max_degree, shared_min, p_max)
    for a, b in pairs:
        if a in flagged and b in flagged:
            link(a, b, "counterparties")

    groups: dict[str, list[str]] = defaultdict(list)
    for eid in sorted(flagged):
        if eid in uf.parent:
            groups[uf.find(eid)].append(eid)

    clusters: dict[str, Cluster] = {}
    for root, members in groups.items():
        if len(members) < 2:
            continue
        c = Cluster(id="", members=members)
        for (a, _b), kinds in link_kind.items():
            if uf.find(a) == root:
                for k in kinds:
                    c.links[k] = c.links.get(k, 0) + 1
        member_set = set(members)
        c.shared_buildings = sorted({buildings[m] for m in members if buildings.get(m)} & set(by_building))
        c.shared_buildings = [k for k in c.shared_buildings if len(set(by_building[k]) & member_set) > 1]
        clusters[root] = c

    for w in wires:
        for eid in (w.originator.entity_id, w.beneficiary.entity_id):
            root = uf.find(eid) if eid in uf.parent else ""
            if root in clusters:
                c = clusters[root]
                c.wires += 1
                c.value_usd += w.amount_usd
                if w.id in review_ids:
                    c.review_wires += 1
                break

    ordered = sorted(clusters.values(), key=lambda c: (-c.value_usd, c.members[0]))
    for n, c in enumerate(ordered, 1):
        c.id = f"C{n:03d}"
    return ordered
