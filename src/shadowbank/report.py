"""Text, JSON and CSV output."""

from __future__ import annotations

import csv
import io
import json
from collections import Counter
from typing import Any

from .calibrate import Calibration
from .codes import CODES, FAMILY_NAMES, SOURCES
from .develop import DevelopmentResult
from .network import Cluster
from .screen import ScreenResult, WireResult

ORDER = {"review": 0, "watch": 1, "note": 2, "clear": 3}


def _wire_dict(r: WireResult) -> dict[str, Any]:
    w = r.wire
    return {
        "id": w.id,
        "date": w.date.isoformat(),
        "amount_usd": str(w.amount_usd),
        "originator": w.originator.entity_id,
        "beneficiary": w.beneficiary.entity_id,
        "disposition": r.disposition,
        "families": r.families,
        "reasons": r.reasons,
        "findings": [
            {
                "code": f.code,
                "family": f.family,
                "severity": f.severity,
                "role": f.role,
                "subject": f.subject,
                "evidence": f.evidence,
                "source": SOURCES[f.source][0],
            }
            for f in r.findings
        ],
    }


def screen_json(res: ScreenResult, clusters: list[Cluster] | None = None) -> str:
    out: dict[str, Any] = {
        "summary": dict(Counter(r.disposition for r in res.wires)),
        "run": [f.evidence for f in res.run_findings],
        "wires": [_wire_dict(r) for r in sorted(res.wires, key=lambda r: (ORDER[r.disposition], r.wire.id))],
        "counterparty_hubs_skipped": sorted(res.hubs),
    }
    if clusters is not None:
        out["clusters"] = [cluster_dict(c) for c in clusters]
    return json.dumps(out, indent=2) + "\n"


def screen_csv(res: ScreenResult) -> str:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(
        [
            "wire_id",
            "date",
            "amount_usd",
            "disposition",
            "code",
            "family",
            "severity",
            "role",
            "subject",
            "evidence",
        ]
    )
    for r in sorted(res.wires, key=lambda r: (ORDER[r.disposition], r.wire.id)):
        if not r.findings:
            w.writerow([r.wire.id, r.wire.date, r.wire.amount_usd, r.disposition, "", "", "", "", "", ""])
        for f in r.findings:
            w.writerow(
                [
                    r.wire.id,
                    r.wire.date,
                    r.wire.amount_usd,
                    r.disposition,
                    f.code,
                    f.family,
                    f.severity,
                    f.role,
                    f.subject,
                    f.evidence,
                ]
            )
    return buf.getvalue()


def screen_text(res: ScreenResult, show: set[str], clusters: list[Cluster] | None = None) -> str:
    counts = Counter(r.disposition for r in res.wires)
    lines = [
        f"{len(res.wires)} wires: "
        + ", ".join(f"{counts.get(d, 0)} {d}" for d in ("review", "watch", "note", "clear")),
    ]
    for f in res.run_findings:
        lines.append(f"  not evaluated: {f.evidence}")
    if res.hubs:
        lines.append(f"  counterparty hubs left out of overlap counts: {len(res.hubs)}")
    for r in sorted(res.wires, key=lambda r: (ORDER[r.disposition], -r.wire.amount_usd, r.wire.id)):
        if r.disposition not in show:
            continue
        w = r.wire
        lines.append("")
        lines.append(
            f"{r.disposition.upper():6} {w.id}  {w.date}  ${w.amount_usd:,.2f}  "
            f"{w.originator.name} -> {w.beneficiary.name}"
        )
        if r.reasons:
            lines.append(f"       why: {'; '.join(r.reasons)}")
        for f in sorted(r.findings, key=lambda f: (f.family, f.code, f.role)):
            if f.severity == "info" and r.disposition != "review":
                continue
            who = "" if f.role in {"wire", "run"} else f"{f.role[:4]} "
            lines.append(f"       {f.code:22} {f.severity:6} {who}{f.evidence}")
    if clusters:
        lines.append("")
        lines.append(f"{len(clusters)} clusters of flagged parties")
        for c in clusters:
            lines.extend(cluster_text(c))
    return "\n".join(lines) + "\n"


def cluster_dict(c: Cluster) -> dict[str, Any]:
    return {
        "id": c.id,
        "members": c.members,
        "links": c.links,
        "wires": c.wires,
        "value_usd": str(c.value_usd),
        "review_wires": c.review_wires,
        "shared_buildings": c.shared_buildings,
    }


def cluster_text(c: Cluster) -> list[str]:
    links = ", ".join(f"{k} {v}" for k, v in sorted(c.links.items()))
    out = [
        f"  {c.id}  {len(c.members)} parties, {c.wires} wires, ${c.value_usd:,.0f}, "
        f"{c.review_wires} for review; links: {links}",
        f"        members: {', '.join(c.members[:8])}{' ...' if len(c.members) > 8 else ''}",
    ]
    for b in c.shared_buildings[:3]:
        out.append(f"        shared building: {b}")
    return out


def develop_text(r: DevelopmentResult) -> str:
    lines = [f"{'origin':>9} {'attributed':>16} {'ultimate':>16} {'not yet':>16} {'s.e.':>14} {'cv':>6}"]
    for o, lt, u, res, se in zip(r.origins, r.latest, r.ultimate, r.unattributed, r.se, strict=True):
        cv = f"{se / res:.2f}" if res > 0 else "-"
        lines.append(f"{o:>9} {lt:16,.0f} {u:16,.0f} {res:16,.0f} {se:14,.0f} {cv:>6}")
    lines.append(
        f"{'total':>9} {r.total_latest:16,.0f} {r.total_latest + r.total_unattributed:16,.0f}"
        f" {r.total_unattributed:16,.0f} {r.total_se:14,.0f} {r.total_cv:6.2f}"
    )
    lines.append("")
    lines.append("age-to-age factors: " + " ".join(f"{x:.4f}" for x in r.factors))
    for n in r.notes:
        lines.append(f"note: {n}")
    return "\n".join(lines) + "\n"


def develop_json(r: DevelopmentResult) -> str:
    return (
        json.dumps(
            {
                "origins": [
                    {"origin": o, "attributed": lt, "ultimate": u, "not_yet_attributed": res, "se": se}
                    for o, lt, u, res, se in zip(
                        r.origins, r.latest, r.ultimate, r.unattributed, r.se, strict=True
                    )
                ],
                "factors": r.factors,
                "sigma2": r.sigma2,
                "total": {
                    "attributed": r.total_latest,
                    "not_yet_attributed": r.total_unattributed,
                    "se": r.total_se,
                    "cv": r.total_cv,
                },
                "notes": r.notes,
            },
            indent=2,
        )
        + "\n"
    )


def calibration_text(c: Calibration) -> str:
    lines = [
        f"{c.labelled} labelled wires, {c.positives} confirmed ({c.base_rate:.1%})",
        "",
        f"{'code':24} {'hits':>6} {'true':>6} {'precision':>9} {'95% interval':>15}"
        f" {'recall':>7} {'lift':>6}",
    ]
    for s in c.codes:
        lines.append(
            f"{s.code:24} {s.hits:6} {s.true_hits:6} {s.precision:9.1%} "
            f"{f'{s.low:.1%}-{s.high:.1%}':>15} {s.recall:7.1%} {s.lift:6.2f}"
        )
    lines.append("")
    lines.append("min_families  review  confirmed  precision  recall")
    for row in c.sweep:
        lines.append(
            f"{row.min_families:12}  {row.review:6}  {row.true_review:9}  "
            f"{row.precision:9.1%}  {row.recall:6.1%}"
        )
    return "\n".join(lines) + "\n"


def codes_text() -> str:
    lines = []
    for code, (fam, sev, src, desc) in CODES.items():
        lines.append(f"{code:24} {FAMILY_NAMES[fam]:20} {sev:6} {desc}")
        lines.append(f"{'':24} source: {SOURCES[src][0]}")
    return "\n".join(lines) + "\n"
