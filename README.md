# shadowbank-screen

Screen wire activity against the patterns in FinCEN's November 2026 Financial Trend Analysis on
Iranian shadow banking, group the parties that keep showing up together, and estimate how much
recent activity your team has not attributed yet.

Built and maintained by Art Akopian, CEO of [Banrox](https://banrox.com).

Engineering checklist, not legal advice.

## Why

On November 23, 2026 FinCEN published
[Iranian Shadow Banking: Update on Trends in Bank Secrecy Act Data](https://www.fincen.gov/sites/default/files/100/FTA-Iran-Shadow-Banking.pdf)
([press release](https://www.fincen.gov/news/news-releases/treasury-identifies-nearly-15-billion-potential-iranian-shadow-banking)).
It covers about $14.7 billion of activity from January 2025 to August 2026: 4,983 transactions of
$500,000 or more that institutions reported and FinCEN could corroborate. The findings read like a
spec for a wire monitoring rule set:

- Bank-location routes: mainland China to the UAE (about $2.6 billion), Singapore to the UAE (about
  $981 million), unidentified jurisdictions to the UAE ($943 million), the UK to the UAE (about
  $922 million).
- Hong Kong-registered companies banking in mainland China originated 73 percent of the Hong
  Kong-originated value.
- DMCC free-zone companies accounted for about 30 percent of UAE-related funds; seven other free
  zones about 25 percent.
- Marshall Islands and BVI companies, "usually at addresses linked to corporate registries".
- Many of the companies had "little to no web presence", "opaque ownership", were "co-located with
  numerous other companies", or were "recently incorporated".
- Multimillion wires over a short timeframe with missing or incomplete source-of-funds
  information, or that did not match the customer's line of business.
- The same companies "frequently appeared in the same financial networks ... with many of the same
  counterparties".
- No everyday operating expenses: no salaries or wages, no miscellaneous business costs.

FinCEN also says there is an attribution lag between when a transaction happens and when it gets
tied to Iran, and it estimates the unattributed part with "concepts from actuarial loss development
methods". Footnote 7 points to Friedland's chapter on the development technique (also called chain
ladder), not to Mack.

Each of those is a check you can run on data a bank or money transmitter already holds. This
package runs them, says which passage of the FTA each one comes from, and keeps them apart so an
analyst can see why a wire came up.

## What it does

| Command | What you get |
| --- | --- |
| `shadowbank screen` | Findings and a disposition (`review`, `watch`, `note`, `clear`) for every wire |
| `shadowbank network` | Clusters of flagged parties linked by transfers, shared buildings or shared counterparties |
| `shadowbank develop` | Chain-ladder estimate of value not yet attributed, per month or quarter, with Mack standard errors |
| `shadowbank calibrate` | Precision, recall and lift of each code against outcomes your investigators recorded |
| `shadowbank codes` | Every finding code with its family, severity and source |

Standard library only, Python 3.11+, no network calls.

## Install

```sh
pip install git+https://github.com/BanroxArt/shadowbank-screen
```

## Worked example

The `examples/` directory holds synthetic data: 180 invented companies, 1,640 wires, a ledger,
outcome labels and 2,537 attribution cases. One network is planted in ordinary trade. Every name,
address and bank in it is made up.

```sh
shadowbank screen examples/wires.csv --entities examples/entities.csv \
    --ledger examples/ledger.csv --registry examples/registry.txt
```

```
1640 wires: 326 review, 298 watch, 17 note, 999 clear

REVIEW W001497  2025-09-07  $6,478,966.00  Quataltus Trading Co Ltd -> Marsenket Petroleum DMCC
       why: medium findings in 3 families: E, N, T
       SB-COLOCATED           medium bene 7 distinct entities at 'TWR 7 KETVIN LAKES RD DUBAI'
       SB-FREEZONE            low    bene free_zone=DMCC
       SB-NO-WEB              low    bene website checked, none found
       SB-OPAQUE              medium orig beneficial owners not disclosed
       SB-YOUNG               medium orig incorporated 2025-02-18, 201 days
       SB-CORRIDOR            low    banks mainland China to UAE; FinCEN total about $2.6 billion
       SB-REG-BANK-SPLIT      low    orig registered in Hong Kong, banks in mainland China
       SB-NET-SHARED-CPTY     medium orig shares counterparties with HK003 (14), HK002 (13), HK001 (12) and 4 more
       SB-BURST               medium orig 10 wires of at least $1,000,000 between 2025-08-10 and 2025-09-07, total $32,825,876
       SB-NO-OPEX             medium orig $197,396,743 through the account over 312 days, no debit in benefits, ...
       SB-SOF-MISSING         medium $6,478,966, purpose '(empty)'
       ...
```

(Trimmed. The real output lists every finding for both parties.)

`--format json` adds the clusters and the source passage for each finding; `--format csv` gives one
row per finding for a case-management import. The exit code is 1 when any wire is for review, so
the command can gate a batch job.

## How a disposition is reached

Every code belongs to one family: geography (`G`), entity profile (`E`), transaction pattern
(`T`), network (`N`) or listed bank (`L`). Severity is `info`, `low`, `medium` or `high`.

- `review`: a party banks at an institution named in a proposed section 311 rule (today only the
  August 28, 2026 proposed rule on Banque Misr UAE, which is not a final action); or medium findings
  in two of `E`, `T` and `N`; or findings in
  `--min-families` families (default 3) with at least one medium finding outside geography.
- `watch`: any low-or-higher finding outside geography.
- `note`: geography only.
- `clear`: nothing above `info`.

Geography never produces `review` by itself. The UAE, Hong Kong and Singapore corridors carry a
large share of legitimate trade, and the FTA describes where flagged money went, not where money
should not go. A team that wants a stricter or looser line changes `--min-families` and checks the
effect with `calibrate` on its own history.

## Networks

`SB-NET-SHARED-CPTY` fires when a party shares counterparties with a party that has its own entity
or transaction findings. Two busy importers share suppliers by chance, so an overlap counts only
when the hypergeometric tail is at most `--shared-p` (default 0.001): with `n` parties in the data
and degrees `da` and `db`, the probability that two random parties share `k` or more
counterparties. Counterparties with more than `--max-degree` neighbours (a freight forwarder every
importer uses) are left out of the overlap count and listed as hubs.

`shadowbank network` joins flagged parties into clusters through direct transfers, shared
buildings and significant counterparty overlap, and reports value, wire count and how many of the
wires are for review. On the example data all 18 planted parties land in one cluster, along with 13
ordinary companies: the six suppliers the network pays (flagged for bursts of large incoming
wires), five young ordinary companies that trade with them, and the two legitimate tenants of the
shared tower. That is what an analyst should see: the cluster is a
starting point for review, and the ordinary members are why it is not a conclusion.

Addresses are reduced to a building key before comparison: case and accents folded, common words
abbreviated, and office, suite, unit and floor numbers dropped, so `Office 1203, Tower 7` and
`OFFICE #905 - TOWER 7` land on the same building.

## Attribution lag

`shadowbank develop` takes cases with a transaction date, an attribution date and an amount, builds
a cumulative triangle (origin period by lag), and applies the chain-ladder method FinCEN pointed to
in Friedland. The standard errors are from Mack (1993), which is this tool's choice for error ranges,
not a method FinCEN cited. The test suite reproduces Mack's published figures on the Taylor and Ashe
triangle to the dollar: total reserve 18,680,856, standard error 2,447,095.

```sh
shadowbank develop examples/cases.csv --period month
```

```
   origin       attributed         ultimate          not yet           s.e.     cv
  ...
  2026-06      259,471,609      473,358,942      213,887,333     47,536,633   0.22
  2026-07      134,467,957      352,947,014      218,479,057     60,702,030   0.28
  2026-08       69,288,045      478,008,544      408,720,499    125,734,749   0.31
    total    7,303,828,408    8,768,640,091    1,464,811,683    187,061,562   0.13
```

FinCEN does not publish its own model, so this is not a reproduction of it. It answers the same
question for a team's own case book: how much of last quarter is still unattributed, and how sure
the estimate is. Chain ladder assumes the lag pattern is stable; if the team changed how it
attributes cases, split the data at the change.

## Back-testing

```sh
shadowbank calibrate examples/wires.csv examples/labels.csv --entities examples/entities.csv \
    --ledger examples/ledger.csv --registry examples/registry.txt
```

prints, for each code, hits, confirmed hits, precision with a Wilson 95 percent interval, recall
and lift over the base rate, then a sweep of `min_families` from 2 to 5. Numbers from the synthetic
data only show the mechanics; they say nothing about how the checks perform on real books.

## Inputs

Wires, entity profiles and ledger postings are CSV or JSON Lines with flat keys. The full schema
is in [docs/format.md](docs/format.md). The short version:

- `wires`: `id, date, amount_usd, orig_name, orig_reg_country, orig_bank_country, orig_bank_name,
  orig_address, bene_*` likewise, `purpose`, `customer` (`originator` or `beneficiary`).
- `--entities`: `entity_id, name, reg_country, free_zone, address, incorporated, website,
  owners_disclosed, line_of_business`. An empty `website` means someone checked and found nothing;
  a missing column or `?` means unknown.
- `--ledger`: `entity_id, date, amount_usd, category`. Debits are negative.
- `--registry`: registry and registered-agent addresses, one per line. No list is shipped; build
  it from your own KYC records.

Checks that need a missing input do not run, and the output says which.

## Limits

- The checks restate the FTA's findings. They are not FinCEN red flags from an advisory, and a hit
  is not a determination of anything. Whether to file a SAR is a judgment for the institution.
- This is not sanctions screening. Run OFAC screening separately. For FinCEN special measures by
  name, see [special-measures](https://github.com/BanroxArt/special-measures).
- The Banque Misr UAE check refers to the August 28, 2026 proposed rule under section 311
  (91 FR 56085), not a final action. Check its status before you act on it.
- Line-of-business matching uses a small keyword table. Expect misses on unusual wording, and add
  your own categories in `normalize.py`.
- Tested on synthetic data only.

## Documentation

- [docs/codes.md](docs/codes.md): every finding code, family, severity, trigger and source page.
- [docs/format.md](docs/format.md): input formats.
- [docs/sources.md](docs/sources.md): primary sources and what each one is used for.
- [SKILL.md](SKILL.md): agent skill for running a review.

## Development

```
pip install -e '.[dev]'
ruff check . && ruff format --check . && python scripts/check.py && mypy && pytest -q
PYTHONPATH=src python bench/run.py 20
```

On 32,800 synthetic wires with 3,562 entities and 124,028 ledger rows, the screen takes about
2.6 s (about 80 microseconds a wire), the network build about 1.4 s, and the development model
over 50,748 cases about 0.1 s.

## License

MIT. See [LICENSE](LICENSE).
