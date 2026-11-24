# Sources

Read on November 24, 2026.

## Primary

- FinCEN, Financial Trend Analysis, "Iranian Shadow Banking: Update on Trends in Bank Secrecy Act
  Data", November 23, 2026 (8 pages; PDF metadata title "BSA Spotlight, Iranian Shadow Banking:
  Update on Trends in Bank Secrecy Act Data, November 23, 2026").
  https://www.fincen.gov/sites/default/files/100/FTA-Iran-Shadow-Banking.pdf
  - p. 2: dataset total and review period; registration and banking-location totals; Hong
    Kong-registered originators banking in mainland China (73 percent, about $3.7 billion).
  - p. 3: Banque Misr UAE and the August 28, 2026 proposed 311 rule (note 2, not a final action);
    DMCC companies "accounted for" about 30 percent of UAE-related funds, and other free zones;
    routes, in this order: mainland China about $2.6 billion, Singapore about $981 million,
    unidentified $943 million, then the UK about $922 million; Marshall Islands and BVI companies
    at registry addresses; banks in the UAE, mainland China, Hong Kong, Singapore, the UK and
    Switzerland; many companies had little to no web presence, opaque ownership, were co-located
    with numerous other companies, or were recently incorporated; multimillion wires with missing
    or incomplete source-of-funds information, or a mismatch with the line of business; shared
    networks and counterparties; no operating expenses.
  - p. 4: BSA data caveat; scope and method, including the $500,000 floor and 4,983 transactions.
  - p. 7: attribution lag and "concepts from actuarial loss development methods"; footnote 7
    cites Friedland's chain-ladder / development-technique chapter
    (https://www.actexmadriver.com/Assets/ClientDocs/prod_preview/A105RC.pdf), not Mack.
- FinCEN press release, "Treasury Identifies Nearly $15 Billion in Potential Iranian Shadow
  Banking", November 23, 2026.
  https://www.fincen.gov/news/news-releases/treasury-identifies-nearly-15-billion-potential-iranian-shadow-banking
- Treasury press release sb0698, same title and date.
  https://home.treasury.gov/news/press-releases/sb0698
- FinCEN, notice of proposed rulemaking under section 311 of the USA PATRIOT Act on Banque Misr
  UAE, issued August 28, 2026, published at 91 FR 56085 (September 1, 2026). Proposed, not a
  final action. https://www.federalregister.gov/d/2026-17871

## Method

- Friedland, Estimating Unpaid Claims Using Basic Techniques, Chapter 7, Development Technique
  (also called chain ladder). This is the source FinCEN cites in footnote 7 of the FTA:
  https://www.actexmadriver.com/Assets/ClientDocs/prod_preview/A105RC.pdf
- Mack, T. (1993). "Distribution-free calculation of the standard error of chain ladder reserve
  estimates." ASTIN Bulletin 23(2), 213-225. Standard error formulas used in `develop.py`,
  including the extrapolation of the last variance parameter. Mack is this tool's choice for
  error ranges; FinCEN did not cite it.
- Taylor, G. C. and Ashe, F. R. (1983). "Second moments of estimates of outstanding claims."
  Journal of Econometrics 23, 37-61. The triangle used in Mack (1993) and in the tests.
- Wilson, E. B. (1927). "Probable inference, the law of succession, and statistical inference."
  Journal of the American Statistical Association 22, 209-212. Interval used in `calibrate`.

## What is ours

The thresholds (except the $500,000 floor), the family and disposition scheme, the free-zone
suffix inference, the building key, the hypergeometric overlap test, the use of chain ladder on a
team's own case data, and the back-testing are this tool's choices. None of them is FinCEN
guidance.
