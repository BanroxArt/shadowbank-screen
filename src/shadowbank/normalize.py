"""Name, address and free-text normalization.

The goal is stable keys, not pretty output: two spellings of one company or one building should
reduce to the same string, and two different buildings should not.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Final

_PUNCT = re.compile(r"[^0-9A-Z#]+")

LEGAL_SUFFIXES: Final = frozenset(
    {
        "LTD",
        "LIMITED",
        "LLC",
        "L",
        "C",
        "FZE",
        "FZCO",
        "FZC",
        "FZ",
        "DMCC",
        "CO",
        "COMPANY",
        "CORP",
        "CORPORATION",
        "INC",
        "INCORPORATED",
        "PTE",
        "PLC",
        "GMBH",
        "AG",
        "SA",
        "SAS",
        "BV",
        "LLP",
        "LP",
        "SARL",
    }
)

_ABBREV: Final = {
    "STREET": "ST",
    "ROAD": "RD",
    "AVENUE": "AVE",
    "BUILDING": "BLDG",
    "BLD": "BLDG",
    "TOWER": "TWR",
    "FLOOR": "FL",
    "SUITE": "STE",
    "OFFICE": "OFC",
    "OFF": "OFC",
    "APARTMENT": "APT",
    "NUMBER": "NO",
    "ISLAND": "IS",
    "CENTRE": "CTR",
    "CENTER": "CTR",
    "COMPLEX": "CPLX",
    "POST": "PO",
    "P": "",
    "O": "",
}

# Tokens that introduce a unit inside a building. The unit value that follows is dropped so that
# "Office 1203, Tower 7" and "Office 905, Tower 7" give the same building key.
_UNIT: Final = frozenset({"OFC", "STE", "UNIT", "FL", "APT", "RM", "ROOM", "FLAT", "DESK", "#"})


def fold(text: str) -> str:
    """Upper case, strip accents, replace punctuation with single spaces."""
    decomposed = unicodedata.normalize("NFKD", text)
    ascii_only = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(_PUNCT.sub(" ", ascii_only.upper()).split())


def name_key(name: str) -> str:
    """Company name with legal-form words removed, for matching spellings of one entity."""
    tokens = fold(name).replace("#", " ").split()
    while tokens and tokens[-1] in LEGAL_SUFFIXES:
        tokens.pop()
    kept = [t for t in tokens if t not in {"THE"}]
    return " ".join(kept)


def entity_key(name: str, reg_country: str) -> str:
    """Fallback entity id when the input has none: folded name plus registration country."""
    key = name_key(name)
    if not key:
        return ""
    return f"{key}|{reg_country.upper()}" if reg_country else key


def address_tokens(address: str) -> list[str]:
    out: list[str] = []
    for tok in fold(address).replace("#", " # ").split():
        tok = _ABBREV.get(tok, tok)
        if tok:
            out.append(tok)
    # "PO BOX" after the P/O drop becomes "BOX"; put it back so it stays visible.
    return ["PO BOX" if t == "BOX" else t for t in out]


def building_key(address: str) -> str:
    """Address with unit, suite, office and floor numbers removed."""
    tokens = address_tokens(address)
    out: list[str] = []
    skip_next = False
    for tok in tokens:
        if skip_next:
            if tok in _UNIT or tok == "NO":
                continue
            skip_next = False
            if any(ch.isdigit() for ch in tok) or len(tok) <= 3:
                continue
        if tok in _UNIT:
            skip_next = True
            continue
        out.append(tok)
    return " ".join(out)


# --- free text: purposes and lines of business ------------------------------------------------

CATEGORY_WORDS: Final[dict[str, tuple[str, ...]]] = {
    "shipping": (
        "FREIGHT",
        "SHIPPING",
        "VESSEL",
        "CHARTER",
        "DEMURRAGE",
        "CARGO",
        "LOGISTICS",
        "MARINE",
        "MARITIME",
        "TANKER",
        "CONTAINER",
        "NAVIGATION",
    ),
    "oil": (
        "CRUDE",
        "OIL",
        "PETROLEUM",
        "BUNKER",
        "BUNKERING",
        "FUEL",
        "DIESEL",
        "GASOIL",
        "NAPHTHA",
        "LPG",
        "PETROCHEMICAL",
        "PETROCHEMICALS",
        "BITUMEN",
        "ENERGY",
    ),
    "metals": ("STEEL", "COPPER", "ALUMINIUM", "ALUMINUM", "METAL", "METALS", "IRON", "ORE"),
    "technology": (
        "ELECTRONIC",
        "ELECTRONICS",
        "COMPONENT",
        "COMPONENTS",
        "SEMICONDUCTOR",
        "SEMICONDUCTORS",
        "COMPUTER",
        "SERVER",
        "SERVERS",
        "SOFTWARE",
        "CHIP",
        "CHIPS",
        "TECHNOLOGY",
        "TECH",
    ),
    "investment": (
        "INVESTMENT",
        "INVESTMENTS",
        "CAPITAL",
        "LOAN",
        "DIVIDEND",
        "SHAREHOLDER",
        "FUND",
        "HOLDING",
        "HOLDINGS",
        "EQUITY",
    ),
    "services": ("CONSULTING", "CONSULTANCY", "ADVISORY", "COMMISSION", "MANAGEMENT", "MARKETING"),
    "food": ("RICE", "SUGAR", "WHEAT", "FOOD", "FOODS", "GRAIN", "TEA", "COFFEE", "FRUIT"),
    "textiles": ("TEXTILE", "TEXTILES", "GARMENT", "GARMENTS", "FABRIC", "YARN", "APPAREL"),
    "trading": ("TRADING", "TRADE", "GENERAL TRADING", "IMPORT", "EXPORT", "COMMODITIES"),
}

# Words that say nothing about what was paid for or where the money came from.
GENERIC_PURPOSE: Final = frozenset(
    {
        "",
        "PAYMENT",
        "PAYMENTS",
        "PMT",
        "TRANSFER",
        "TRF",
        "INVOICE",
        "INV",
        "SETTLEMENT",
        "GOODS",
        "TRADE",
        "TRADING",
        "CONTRACT",
        "AS PER CONTRACT",
        "AS PER INVOICE",
        "REMITTANCE",
        "FUNDS",
        "FUND TRANSFER",
        "OTHER",
        "OTHERS",
        "NA",
        "N A",
        "NONE",
        "MISC",
        "BUSINESS",
        "PURCHASE",
        "SERVICES",
    }
)

_FILLER: Final = frozenset({"FOR", "OF", "THE", "AND", "PER", "AS", "TO", "REF", "NO", "PAYMENT", "PMT"})

# Purpose categories a line of business can plausibly pay or be paid for.
COMPATIBLE: Final[dict[str, frozenset[str]]] = {
    "trading": frozenset({"trading", "oil", "metals", "technology", "food", "textiles", "shipping"}),
    "shipping": frozenset({"shipping", "oil"}),
    "oil": frozenset({"oil", "shipping"}),
    "metals": frozenset({"metals", "shipping"}),
    "technology": frozenset({"technology", "services"}),
    "investment": frozenset({"investment"}),
    "services": frozenset({"services"}),
    "food": frozenset({"food", "shipping"}),
    "textiles": frozenset({"textiles", "shipping"}),
}

SECTOR_CATEGORIES: Final = ("shipping", "oil", "trading", "investment", "technology")


def categories(text: str) -> list[str]:
    """Business categories mentioned in free text, in CATEGORY_WORDS order."""
    folded = f" {fold(text)} "
    found: list[str] = []
    for cat, words in CATEGORY_WORDS.items():
        if any(f" {w} " in folded for w in words):
            found.append(cat)
    return found


def is_generic_purpose(purpose: str) -> bool:
    """True when the purpose text carries no information about what the money is for.

    Invoice and contract numbers do not count as information; neither does a bare "goods".
    """
    folded = fold(purpose)
    if folded in GENERIC_PURPOSE:
        return True
    words = [w for w in folded.split() if w not in _FILLER and not any(ch.isdigit() for ch in w)]
    return " ".join(words) in GENERIC_PURPOSE or all(w in GENERIC_PURPOSE for w in words)


def free_zone_marker(name: str, address: str, declared: str) -> str:
    """Why a UAE party looks free-zone registered, or "" when it does not."""
    if declared.strip():
        return f"free_zone={declared.strip()}"
    for label, text in (("name", name), ("address", address)):
        folded = f" {fold(text)} "
        if " DMCC " in folded:
            return f"DMCC in {label}"
        if " JAFZA " in folded or " FREE ZONE " in folded or " FREEZONE " in folded:
            return f"free zone in {label}"
    toks = fold(name).split()
    for i, tok in enumerate(toks):
        if tok in {"FZE", "FZCO", "FZC"}:
            return f"{tok} suffix"
        if tok == "FZ" and i + 1 < len(toks) and toks[i + 1] == "LLC":
            return "FZ-LLC suffix"
    return ""
