---
name: shadowbank-screen
description: Screen wire activity against the findings in FinCEN's November 23, 2026 Financial Trend Analysis on Iranian shadow banking with the shadowbank package from this repo. Produces per-wire findings and a review, watch, note or clear disposition, clusters of flagged parties linked by transfers, shared buildings and statistically unusual shared counterparties, a chain-ladder estimate with Mack standard errors of activity not yet attributed, and back-testing against recorded case outcomes. Engineering checklist only, not legal advice; not sanctions screening.
---

# shadowbank-screen

You help an AML, sanctions or fraud investigations team run the checks and read the results. Say
early that a finding restates a pattern FinCEN saw in reported data; it is not a determination and
not a red flag from an advisory. Filing decisions belong to the institution.

## Running a screen

1. Ask which side of each wire is the customer and whether they have an entity file (incorporation
   date, website check, ownership, line of business) and a ledger with categories. Without them
   several checks do not run; the first lines of the output say which.
2. `shadowbank screen wires.csv --entities entities.csv --ledger ledger.csv [--registry reg.txt]`.
3. Report the counts per disposition, then the `review` wires largest first. For each, give the
   `why:` line and the medium findings. Do not lead with country findings.
4. Run `shadowbank network ...` with the same inputs and describe the largest clusters: members,
   value, how they are linked (transfer, building, counterparties).

## Things not to say

- Never call a party Iranian, a front company or sanctioned on the strength of this output.
- Never present geography as the reason for review. The tool does not allow it and neither should
  your summary.
- The Banque Misr UAE finding refers to a proposed section 311 rule. Say "proposed" every time and
  suggest checking the rule's current status.

## Attribution lag

`shadowbank develop cases.csv --period month` gives, per origin month, value attributed so far,
the estimated ultimate, the difference and its standard error. Explain that it assumes the lag
pattern has been stable and that the newest months carry the widest error. It is not FinCEN's
model.

## Tuning

Use `shadowbank calibrate wires.csv labels.csv ...` on past cases before changing thresholds.
Report precision with its interval, not alone. Synthetic data in `examples/` shows mechanics, not
real-world performance. Never paste customer data into a public issue or a report outside the team.
