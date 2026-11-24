"""Finding codes and the passages they come from.

Every code names one indicator family:

- ``G`` geography: where the parties are registered and where they bank.
- ``E`` entity profile: what the registration and the public footprint look like.
- ``T`` transaction pattern: what the money does.
- ``N`` network: who else the party trades with or shares an address with.
- ``L`` listed: a bank named in a proposed FinCEN section 311 rule (not a final action).

Severity is one of ``info``, ``low``, ``medium``, ``high``. ``info`` findings are context and never
move a disposition on their own.
"""

from __future__ import annotations

from typing import Final, Literal

Family = Literal["G", "E", "T", "N", "L"]
Severity = Literal["info", "low", "medium", "high"]

FTA_URL: Final = "https://www.fincen.gov/sites/default/files/100/FTA-Iran-Shadow-Banking.pdf"

# key -> (citation, url)
SOURCES: Final[dict[str, tuple[str, str]]] = {
    "fta-p2": (
        "FinCEN, Financial Trend Analysis, Iranian Shadow Banking: Update on Trends in Bank Secrecy"
        " Act Data (Nov 23, 2026), p. 2, Key Updates and Findings",
        FTA_URL,
    ),
    "fta-p3": ("FinCEN FTA, Iranian Shadow Banking (Nov 23, 2026), p. 3", FTA_URL),
    "fta-p4": ("FinCEN FTA, Iranian Shadow Banking (Nov 23, 2026), p. 4, Scope and Methodology", FTA_URL),
    "fta-p3-fn2": (
        "FinCEN FTA, Iranian Shadow Banking (Nov 23, 2026), p. 3 note 2; August 28, 2026 proposed"
        " section 311 rule on Banque Misr UAE, 91 FR 56085 (Sep 1, 2026), not a final action",
        "https://www.federalregister.gov/d/2026-17871",
    ),
    "own": ("This tool's own check, built on the FTA findings it names; not a FinCEN indicator", ""),
}

# code -> (family, severity, source key, one-line trigger)
CODES: Final[dict[str, tuple[Family, Severity, str, str]]] = {
    "SB-SCOPE-VALUE": (
        "T",
        "info",
        "fta-p4",
        "Wire is at or above the $500,000 floor FinCEN used to build its dataset.",
    ),
    "SB-CORRIDOR": (
        "G",
        "low",
        "fta-p3",
        "Bank-location corridor is one FinCEN lists as most common, in this order: mainland China,"
        " Singapore, an unidentified jurisdiction or the United Kingdom to the UAE.",
    ),
    "SB-HUB-REG": (
        "G",
        "info",
        "fta-p2",
        "A party is registered in the UAE, Hong Kong or Singapore.",
    ),
    "SB-HUB-BANK": (
        "G",
        "info",
        "fta-p3",
        "A party banks in the UAE, mainland China, Hong Kong, Singapore, the UK or Switzerland.",
    ),
    "SB-REG-BANK-SPLIT": (
        "G",
        "low",
        "fta-p2",
        "A party registered in one hub jurisdiction banks in another, as Hong Kong companies banking"
        " in mainland China did for 73 percent of Hong Kong-originated value.",
    ),
    "SB-FREEZONE": (
        "E",
        "low",
        "fta-p3",
        "UAE party registered in a free zone (DMCC named by FinCEN; other zones inferred from the"
        " free_zone field or an FZE, FZCO, FZC or FZ-LLC suffix).",
    ),
    "SB-OFFSHORE": (
        "E",
        "low",
        "fta-p3",
        "Party registered in the Marshall Islands or the British Virgin Islands.",
    ),
    "SB-OFFSHORE-REGISTRY": (
        "E",
        "medium",
        "fta-p3",
        "Marshall Islands or BVI party whose address is a registry or registered-agent address you"
        " supplied, or is shared by many other entities.",
    ),
    "SB-COLOCATED": (
        "E",
        "medium",
        "fta-p3",
        "The party's building is shared by at least `colocated_min` distinct entities in your data.",
    ),
    "SB-YOUNG": (
        "E",
        "medium",
        "fta-p3",
        "Party was incorporated less than `young_days` before the wire.",
    ),
    "SB-NO-WEB": ("E", "low", "fta-p3", "Party has no web presence on record."),
    "SB-OPAQUE": ("E", "medium", "fta-p3", "Beneficial ownership is recorded as not disclosed."),
    "SB-SECTOR": (
        "E",
        "info",
        "fta-p3",
        "Party is in shipping, oil, trading, investment or technology procurement.",
    ),
    "SB-SOF-MISSING": (
        "T",
        "medium",
        "fta-p3",
        "Multimillion wire with missing or incomplete source-of-funds or purpose text.",
    ),
    "SB-LOB-MISMATCH": (
        "T",
        "medium",
        "fta-p3",
        "Wire purpose falls in a different business category from the customer's line of business.",
    ),
    "SB-BURST": (
        "T",
        "medium",
        "fta-p3",
        "Party sent or received `burst_count` or more wires of at least `burst_min` within"
        " `burst_days` days.",
    ),
    "SB-NO-OPEX": (
        "T",
        "medium",
        "fta-p3",
        "Ledger shows large flows and no payroll, rent, utilities, tax or other operating expense.",
    ),
    "SB-NET-SHARED-CPTY": (
        "N",
        "medium",
        "fta-p3",
        "Party shares `shared_min` or more counterparties with another party that has its own"
        " entity or transaction findings.",
    ),
    "SB-NET-SHARED-ADDR": (
        "N",
        "low",
        "fta-p3",
        "Party shares a building with another party that has its own entity or transaction findings.",
    ),
    "SB-BANK-311-PROPOSED": (
        "L",
        "high",
        "fta-p3-fn2",
        "A party banks at Banque Misr in the UAE, subject of the August 28, 2026 proposed (not"
        " final) section 311 rule.",
    ),
    "SB-SCOPE-NOT-EVALUATED": (
        "E",
        "info",
        "own",
        "One or more checks could not run because the input lacks the fields they need.",
    ),
}

FAMILY_NAMES: Final[dict[Family, str]] = {
    "G": "geography",
    "E": "entity profile",
    "T": "transaction pattern",
    "N": "network",
    "L": "listed bank",
}

SEVERITY_RANK: Final[dict[Severity, int]] = {"info": 0, "low": 1, "medium": 2, "high": 3}
