# Contributing

Useful contributions:

- New checks tied to a specific passage of a FinCEN, OFAC or other public primary source, with the
  quote, the page and a test.
- Better purpose and line-of-business categories, with examples of wording they catch and wording
  they must not catch.
- Readers for common wire formats (ISO 20022 pacs.008, MT103 exports) that produce the CSV in
  docs/format.md, with a synthetic fixture.

Code changes:

- `ruff check .`, `ruff format --check .`, `python scripts/check.py`, `mypy` and `pytest -q` must pass.
- Standard library only at runtime. No network calls.
- Every code goes in `src/shadowbank/codes.py` and `docs/codes.md`; a test enforces it.
- Synthetic data only. Never commit a real wire, customer, account or case.
- No check may put a wire up for review on geography alone.
