# Sources

Read on November 24, 2026.

## Primary

- FinCEN, Financial Trend Analysis, "Iranian Shadow Banking: Update on Trends in Bank Secrecy Act
  Data", November 23, 2026 (8 pages; PDF metadata title "BSA Spotlight, Iranian Shadow Banking:
  Update on Trends in Bank Secrecy Act Data, November 23, 2026").
  https://www.fincen.gov/sites/default/files/100/FTA-Iran-Shadow-Banking.pdf
  - p. 2: dataset total and review period; registration and banking-location totals; Hong
    Kong-registered originators banking in mainland China (73 percent, about $3.7 billion).
  - p. 3: Banque Misr UAE and the proposed 311 rule (note 2); DMCC and other free zones; routes;
    Marshall Islands and BVI companies at registry addresses; banks in the UAE, mainland China,
    Hong Kong, Singapore, the UK and Switzerland; little or no web presence, opaque ownership,
    co-location, recent incorporation; multimillion wires without source-of-funds information or
    outside the line of business; shared networks and counterparties; no operating expenses.
  - p. 4: BSA data caveat; scope and method, including the $500,000 floor and 4,983 transactions.
  - p. 7: attribution lag and the loss-development approach.
- FinCEN press release, "Treasury Identifies Nearly $15 Billion in Potential Iranian Shadow
  Banking", November 23, 2026.
  https://www.fincen.gov/news/news-releases/treasury-identifies-nearly-15-billion-potential-iranian-shadow-banking
- Treasury press release sb0698, same title and date.
  https://home.treasury.gov/news/press-releases/sb0698
- FinCEN, proposed rule under section 311 of the USA PATRIOT Act on Banque Misr UAE, 91 FR 56085
  (September 1, 2026). Proposed, not final. https://www.federalregister.gov/d/2026-17871

## Method

- Mack, T. (1993). "Distribution-free calculation of the standard error of chain ladder reserve
  estimates." ASTIN Bulletin 23(2), 213-225. Standard error formulas used in `develop.py`,
  including the extrapolation of the last variance parameter.
- Taylor, G. C. and Ashe, F. R. (1983). "Second moments of estimates of outstanding claims."
  Journal of Econometrics 23, 37-61. The triangle used in Mack (1993) and in the tests.
- Wilson, E. B. (1927). "Probable inference, the law of succession, and statistical inference."
  Journal of the American Statistical Association 22, 209-212. Interval used in `calibrate`.

## What is ours

The thresholds (except the $500,000 floor), the family and disposition scheme, the free-zone
suffix inference, the building key, the hypergeometric overlap test, the use of chain ladder on a
team's own case data, and the back-testing are this tool's choices. None of them is FinCEN
guidance.
