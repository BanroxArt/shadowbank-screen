# Input formats

All inputs are UTF-8 CSV with a header row, or JSON Lines (`.jsonl`, `.ndjson`) with one flat
object per line. Unknown columns are ignored (entity extras are kept in `Entity.extra`). Dates are
ISO 8601; anything after the first ten characters is ignored. Amounts may carry `$` and thousands
separators. Countries are ISO 3166-1 alpha-2; anything else is treated as unknown.

## Wires

| Column | Required | Notes |
| --- | --- | --- |
| `id` | yes | Unique. Duplicates are an error. |
| `date` | yes | Value date. |
| `amount_usd` | yes | Non-negative. Convert other currencies first. |
| `orig_name`, `bene_name` | yes | |
| `orig_id`, `bene_id` | no | Your entity id. Without it the id is the folded name with legal-form words removed, plus the registration country. |
| `orig_reg_country`, `bene_reg_country` | no | Country of registration. |
| `orig_bank_country`, `bene_bank_country` | no | Country of the bank holding the account. Empty on the originating side counts as an unidentified jurisdiction for `SB-CORRIDOR`. |
| `orig_bank_name`, `bene_bank_name` | no | Used for the section 311 check. |
| `orig_address`, `bene_address` | no | Used when the entity file has no address. |
| `purpose` | no | Remittance or purpose text as received. |
| `customer` | no | `originator` or `beneficiary`: which side is your customer. Used by `SB-LOB-MISMATCH`. Empty checks both sides. |

## Entities (`--entities`)

| Column | Notes |
| --- | --- |
| `entity_id` | Matches `orig_id` / `bene_id`, or the derived id. |
| `name`, `reg_country`, `address` | Override the values on the wire. |
| `free_zone` | Name of the UAE free zone, if known (for example `DMCC`). |
| `incorporated` | Date of incorporation. |
| `website` | Empty: checked, none found. `?` or column absent: unknown. Anything else: the site. |
| `owners_disclosed` | `yes`/`no` (also `true`/`false`, `1`/`0`). Anything else is unknown. |
| `line_of_business` | Free text from KYC, for example `oil trading`. |

## Ledger (`--ledger`)

| Column | Notes |
| --- | --- |
| `entity_id` | |
| `date` | |
| `amount_usd` | Negative for debits. |
| `category` | Lower-cased on read. A debit in any of `payroll, salary, wages, rent, utilities, tax, insurance, office, opex, benefits` counts as an operating expense. |

## Registry addresses (`--registry`)

One address per line; blank lines and lines starting with `#` are skipped. Each is reduced to a
building key, so unit and suite numbers do not matter.

## Attribution cases (`develop`)

| Column | Notes |
| --- | --- |
| `txn_date` | When the transaction happened. |
| `attributed_date` | When your team tied it to the network. Not before `txn_date`. |
| `amount_usd` | |

Cases attributed after `--as-of` are left out and counted in the notes.

## Labels (`calibrate`)

`wire_id, label`, where label is `1` (confirmed concern) or `0` (closed). Wires without a label are
left out.
