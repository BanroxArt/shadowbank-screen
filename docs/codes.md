# Finding codes

Family: G geography, E entity profile, T transaction pattern, N network, L listed bank.
Severity `info` is context and never moves a disposition. Page numbers are the printed page numbers of
the FinCEN FTA of November 23, 2026. Defaults in backticks are `Config` fields and CLI options.

| Code | Family | Severity | Trigger | Source |
| --- | --- | --- | --- | --- |
| `SB-SCOPE-VALUE` | T | info | Wire is at or above the $500,000 floor FinCEN used to build its dataset. | FinCEN FTA, Iranian Shadow Banking (Nov 23, 2026), p. 4, Scope and Methodology |
| `SB-CORRIDOR` | G | low | Bank-location corridor is one FinCEN lists as most common, in this order: mainland China, Singapore, an unidentified jurisdiction or the United Kingdom to the UAE. | FinCEN FTA, Iranian Shadow Banking (Nov 23, 2026), p. 3 |
| `SB-HUB-REG` | G | info | A party is registered in the UAE, Hong Kong or Singapore. | FinCEN, Financial Trend Analysis, Iranian Shadow Banking: Update on Trends in Bank Secrecy Act Data (Nov 23, 2026), p. 2, Key Updates and Findings |
| `SB-HUB-BANK` | G | info | A party banks in the UAE, mainland China, Hong Kong, Singapore, the UK or Switzerland. | FinCEN FTA, Iranian Shadow Banking (Nov 23, 2026), p. 3 |
| `SB-REG-BANK-SPLIT` | G | low | A party registered in one hub jurisdiction banks in another, as Hong Kong companies banking in mainland China did for 73 percent of Hong Kong-originated value. | FinCEN, Financial Trend Analysis, Iranian Shadow Banking: Update on Trends in Bank Secrecy Act Data (Nov 23, 2026), p. 2, Key Updates and Findings |
| `SB-FREEZONE` | E | low | UAE party registered in a free zone (DMCC named by FinCEN; other zones inferred from the free_zone field or an FZE, FZCO, FZC or FZ-LLC suffix). | FinCEN FTA, Iranian Shadow Banking (Nov 23, 2026), p. 3 |
| `SB-OFFSHORE` | E | low | Party registered in the Marshall Islands or the British Virgin Islands. | FinCEN FTA, Iranian Shadow Banking (Nov 23, 2026), p. 3 |
| `SB-OFFSHORE-REGISTRY` | E | medium | Marshall Islands or BVI party whose address is a registry or registered-agent address you supplied, or is shared by many other entities. | FinCEN FTA, Iranian Shadow Banking (Nov 23, 2026), p. 3 |
| `SB-COLOCATED` | E | medium | The party's building is shared by at least `colocated_min` distinct entities in your data. | FinCEN FTA, Iranian Shadow Banking (Nov 23, 2026), p. 3 |
| `SB-YOUNG` | E | medium | Party was incorporated less than `young_days` before the wire. | FinCEN FTA, Iranian Shadow Banking (Nov 23, 2026), p. 3 |
| `SB-NO-WEB` | E | low | Party has no web presence on record. | FinCEN FTA, Iranian Shadow Banking (Nov 23, 2026), p. 3 |
| `SB-OPAQUE` | E | medium | Beneficial ownership is recorded as not disclosed. | FinCEN FTA, Iranian Shadow Banking (Nov 23, 2026), p. 3 |
| `SB-SECTOR` | E | info | Party is in shipping, oil, trading, investment or technology procurement. | FinCEN FTA, Iranian Shadow Banking (Nov 23, 2026), p. 3 |
| `SB-SOF-MISSING` | T | medium | Multimillion wire with missing or incomplete source-of-funds or purpose text. | FinCEN FTA, Iranian Shadow Banking (Nov 23, 2026), p. 3 |
| `SB-LOB-MISMATCH` | T | medium | Wire purpose falls in a different business category from the customer's line of business. | FinCEN FTA, Iranian Shadow Banking (Nov 23, 2026), p. 3 |
| `SB-BURST` | T | medium | Party sent or received `burst_count` or more wires of at least `burst_min` within `burst_days` days. | FinCEN FTA, Iranian Shadow Banking (Nov 23, 2026), p. 3 |
| `SB-NO-OPEX` | T | medium | Ledger shows large flows and no payroll, rent, utilities, tax or other operating expense. | FinCEN FTA, Iranian Shadow Banking (Nov 23, 2026), p. 3 |
| `SB-NET-SHARED-CPTY` | N | medium | Party shares `shared_min` or more counterparties with another party that has its own entity or transaction findings. | FinCEN FTA, Iranian Shadow Banking (Nov 23, 2026), p. 3 |
| `SB-NET-SHARED-ADDR` | N | low | Party shares a building with another party that has its own entity or transaction findings. | FinCEN FTA, Iranian Shadow Banking (Nov 23, 2026), p. 3 |
| `SB-BANK-311-PROPOSED` | L | high | A party banks at Banque Misr in the UAE, subject of the August 28, 2026 proposed (not final) section 311 rule. | FinCEN FTA, Iranian Shadow Banking (Nov 23, 2026), p. 3 note 2; August 28, 2026 proposed section 311 rule on Banque Misr UAE, 91 FR 56085 (Sep 1, 2026), not a final action |
| `SB-SCOPE-NOT-EVALUATED` | E | info | One or more checks could not run because the input lacks the fields they need. | This tool's own check, built on the FTA findings it names; not a FinCEN indicator |

## Defaults

| Setting | Default | Used by |
| --- | --- | --- |
| `scope_min` | $500,000 | `SB-SCOPE-VALUE` (FinCEN's dataset floor, p. 4) |
| `sof_min` | $1,000,000 | `SB-SOF-MISSING` ("multimillion" in the FTA; the exact cut is ours) |
| `young_days` | 365 | `SB-YOUNG` |
| `colocated_min` | 5 | `SB-COLOCATED`, `SB-OFFSHORE-REGISTRY` |
| `burst_min`, `burst_count`, `burst_days` | $1,000,000, 3, 30 | `SB-BURST` |
| `opex_min_flow`, `opex_min_days` | $1,000,000, 60 | `SB-NO-OPEX` |
| `shared_min`, `shared_p`, `max_counterparty_degree` | 2, 0.001, 50 | `SB-NET-SHARED-CPTY`, `network` |
| `min_families` | 3 | disposition |

Every number in this table except `scope_min` is this tool's default, not FinCEN's. Change them and
check the effect with `shadowbank calibrate`.
