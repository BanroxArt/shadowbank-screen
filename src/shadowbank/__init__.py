"""Screen wire activity against the typologies in FinCEN's November 2026 Iranian shadow banking
Financial Trend Analysis, link the parties into networks, and estimate attribution lag.

Engineering checklist, not legal advice.
"""

from __future__ import annotations

from .codes import CODES, SOURCES
from .develop import DevelopmentResult, chain_ladder
from .model import Entity, LedgerEntry, Party, Wire
from .network import Cluster, build_network
from .screen import Config, Finding, WireResult, screen

__all__ = [
    "CODES",
    "SOURCES",
    "Cluster",
    "Config",
    "DevelopmentResult",
    "Entity",
    "Finding",
    "LedgerEntry",
    "Party",
    "Wire",
    "WireResult",
    "build_network",
    "chain_ladder",
    "screen",
]

__version__ = "0.1.0"
