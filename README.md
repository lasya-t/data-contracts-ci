# Data Contracts Enforced in CI

The checkout team publishes order events that three other teams build on (finance, fraud, customer 360). This project makes the shape of those events a **versioned contract**: a YAML file in the repo, checked on every pull request and enforced on the data itself.

```
contracts/orders.yaml ──▶ PR check: is this change safe for consumers?   (blocks breaking changes)
                      └─▶ runtime: does each batch of events follow it?  (rejects bad records)
```

## The contract

```yaml
name: orders
version: 1.2.0
owner: checkout-team
fields:
  order_id:  {type: string, required: true, pattern: "^O[0-9]{7}$"}
  status:    {type: string, required: true, enum: [placed, paid, shipped, cancelled, returned]}
  amount:    {type: number, required: true, min: 0}
  promo_code:{type: string, required: false}
  ...
```

The same file generates a Pydantic model at runtime (`Contract.to_model()`). Unknown fields are rejected.

## What counts as breaking

The rules are judged **from the consumer's side**:

| Change | Verdict | Why |
|---|---|---|
| remove or rename a field | BREAKING | consumer queries reference it |
| change a type | BREAKING | |
| required → optional | BREAKING | consumers suddenly get nulls |
| **add an enum value** | BREAKING | `CASE WHEN status = ...` mappings silently miss it |
| loosen `min` / `max`, drop a pattern | BREAKING | "impossible" values start to appear |
| add a field (required or optional) | safe | consumers ignore what they don't read |
| remove an enum value, tighten a bound | safe | consumers just see fewer kinds of values |

**The rule CI enforces:** any change needs a version bump, and a breaking change needs a **major** bump (which signals that consumers need a migration plan).

## Example proposals (`examples/proposals/`)

```
01 add optional gift_wrap      1.2.0 -> 1.3.0   [SAFE] field added                 PASS
02 add status "on_hold"        1.2.0 -> 1.3.0   [BREAKING] enum values added       FAIL: needs 2.0.0
03 rename amount               1.2.0 -> 1.3.0   [BREAKING] amount: field removed   FAIL: needs 2.0.0
04 same rename as v2           1.2.0 -> 2.0.0                                       PASS
05 accept any currency         1.2.0 -> 1.3.0   [BREAKING] enum restriction removed FAIL
```

Proposal 05 surfaced a bug in the first version of the checker: dropping the whole enum also printed a misleading "enum values removed ['USD']". The fix and its regression test are their own commit.

## Validating data

```
$ python -m contracts validate contracts/orders.yaml examples/orders_batch.jsonl
2000 records, 1980 valid, 20 rejected (1.00%)
       8  status: literal_error         <- "on_hold" sent before the contract allows it
       5  amount: greater_than_equal    <- refunds sent as negative orders
       4  currency: literal_error       <- CAD
       3  channel: missing
```

The command exits with code 1 when the reject rate goes above `--max-reject-rate`, so a pipeline can stop before loading.

## CI

`.github/workflows/contracts.yml` runs on each pull request. It finds every changed `contracts/*.yaml`, fetches the version on the target branch with `git show`, and runs `contracts check`. A breaking change without a major version bump fails the check.

## How to run

```bash
pip install -r requirements.txt
python examples/make_batch.py
PYTHONPATH=src python -m contracts check contracts/orders.yaml examples/proposals/02_add_status_on_hold.yaml
PYTHONPATH=src python -m contracts validate contracts/orders.yaml examples/orders_batch.jsonl
pytest
```

## Next steps
- Generate JSON Schema / Avro from the same YAML for other languages
- Notify each consumer listed in the contract when a major version is proposed
