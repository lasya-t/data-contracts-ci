import argparse
import json
import sys

from .compat import verdict
from .model import Contract
from .validate import validate_batch


def main() -> None:
    p = argparse.ArgumentParser(prog="contracts")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="compare a proposed contract with the current one")
    c.add_argument("current")
    c.add_argument("proposed")
    v = sub.add_parser("validate", help="validate a JSON Lines file against a contract")
    v.add_argument("contract")
    v.add_argument("data")
    v.add_argument("--max-reject-rate", type=float, default=0.01)
    a = p.parse_args()

    if a.cmd == "check":
        old, new = Contract.load(a.current), Contract.load(a.proposed)
        ok, changes, reason = verdict(old, new)
        print(f"{old.name}: {old.version} -> {new.version}")
        for ch in changes:
            print(f"  [{ch.severity:8s}] {ch.field}: {ch.message}")
        print(("PASS: " if ok else "FAIL: ") + reason)
        sys.exit(0 if ok else 1)

    contract = Contract.load(a.contract)
    with open(a.data) as f:
        records = [json.loads(line) for line in f if line.strip()]
    rep = validate_batch(contract, records)
    print(f"{rep.total} records, {len(rep.valid)} valid, {len(rep.rejected)} rejected ({rep.reject_rate:.2%})")
    for reason, n in rep.reasons.most_common(10):
        print(f"  {n:6d}  {reason}")
    sys.exit(0 if rep.reject_rate <= a.max_reject_rate else 1)


if __name__ == "__main__":
    main()
