from __future__ import annotations

import re
from pathlib import Path

from shadowbank.codes import CODES, SOURCES

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src" / "shadowbank"


def test_every_code_is_documented_and_no_stale_codes() -> None:
    doc = (ROOT / "docs" / "codes.md").read_text()
    rows = set(re.findall(r"^\| `(SB-[A-Z0-9-]+)` \|", doc, re.M))
    assert rows == set(CODES)


def test_every_emitted_code_is_registered_and_used() -> None:
    src = "".join(p.read_text() for p in SRC.glob("*.py") if p.name != "codes.py")
    emitted = set(re.findall(r'"(SB-[A-Z0-9]+(?:-[A-Z0-9]+)*)"', src))
    assert emitted == set(CODES)


def test_sources_are_fincen_or_marked_ours() -> None:
    for key, (cite, url) in SOURCES.items():
        if key == "own":
            assert "own" in cite and url == ""
        else:
            assert url.startswith("https://www.fincen.gov/") or url.startswith(
                "https://www.federalregister.gov/"
            )


def test_codes_doc_matches_family_and_severity() -> None:
    rows = re.findall(
        r"^\| `(SB-[A-Z0-9-]+)` \| (\w) \| (\w+) \|", (ROOT / "docs" / "codes.md").read_text(), re.M
    )
    assert rows
    for code, fam, sev in rows:
        assert CODES[code][:2] == (fam, sev), code


def test_banque_misr_is_always_called_proposed() -> None:
    for name in ["README.md", "SKILL.md", "docs/sources.md", "docs/codes.md"]:
        for line in (ROOT / name).read_text().splitlines():
            if "Banque Misr" in line:
                assert "propos" in line.lower(), (name, line)


def test_attribution_and_disclaimer() -> None:
    readme = (ROOT / "README.md").read_text()
    assert "Built and maintained by Art Akopian, CEO of [Banrox](https://banrox.com)." in readme
    for name in ["README.md", "SKILL.md", "CITATION.cff", "llms.txt", "pyproject.toml"]:
        assert "not legal advice" in (ROOT / name).read_text(), name


def test_fta_figures_quoted_consistently() -> None:
    from shadowbank.screen import CORRIDORS

    readme = (ROOT / "README.md").read_text()
    assert set(CORRIDORS.values()) == {
        "about $2.6 billion",
        "about $981 million",
        "$943 million",
        "about $922 million",
    }
    for v in CORRIDORS.values():
        assert v.replace("about ", "") in readme
    assert "4,983" in readme and "$14.7 billion" in readme and "73 percent" in readme


def test_docs_do_not_call_findings_red_flags_or_requirements() -> None:
    names = ["README.md", "SKILL.md", "llms.txt", "CITATION.cff", "docs/codes.md", "docs/sources.md"]
    text = " ".join((ROOT / n).read_text() for n in names).lower()
    assert "fincen requires" not in text
    assert "not a red flag" in text or "not fincen red flags" in text
