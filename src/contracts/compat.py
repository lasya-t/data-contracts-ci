"""Compare two versions of a contract and classify every change.

BREAKING  - existing consumers can fail or silently compute the wrong thing
SAFE      - existing consumers keep working

From the consumer's point of view:
    remove a field                      BREAKING  (their queries reference it)
    change a field's type               BREAKING
    make an optional field required     SAFE for consumers, but it is the producer promising more
    make a required field optional      BREAKING  (consumers may not handle nulls)
    add a required field                SAFE      (consumers ignore what they don't use)
    add an optional field               SAFE
    remove an enum value                SAFE      (consumers just never see it)
    add an enum value                   BREAKING  (CASE WHEN / mappings miss the new value)
    tighten min/max/pattern             SAFE
    loosen min/max/pattern              BREAKING  (values consumers assumed impossible appear)

Rule enforced in CI: a breaking change needs a major version bump; any change needs some bump.
"""
from __future__ import annotations

from dataclasses import dataclass

from .model import Contract, FieldSpec

BREAKING, SAFE = "BREAKING", "SAFE"


@dataclass
class Change:
    severity: str
    field: str
    message: str


def _bound_change(name, what, old, new, lower_is_looser):
    if old == new:
        return None
    if old is None:
        return Change(SAFE, name, f"{what} added ({new})")
    if new is None:
        return Change(BREAKING, name, f"{what} removed (was {old})")
    looser = new < old if lower_is_looser else new > old
    return Change(BREAKING if looser else SAFE, name, f"{what} {old} -> {new}")


def _field_changes(o: FieldSpec, n: FieldSpec) -> list[Change]:
    out = []
    if o.type != n.type:
        out.append(Change(BREAKING, o.name, f"type {o.type} -> {n.type}"))
    if o.required and not n.required:
        out.append(Change(BREAKING, o.name, "required -> optional (consumers may now get nulls)"))
    if not o.required and n.required:
        out.append(Change(SAFE, o.name, "optional -> required"))
    if o.enum != n.enum:
        old, new = set(o.enum or ()), set(n.enum or ())
        if o.enum is not None and n.enum is None:
            out.append(Change(BREAKING, o.name, "enum restriction removed (any value allowed)"))
        elif new - old:
            out.append(Change(BREAKING, o.name, f"enum values added {sorted(new - old)}"))
        if o.enum is not None and n.enum is not None and old - new:
            out.append(Change(SAFE, o.name, f"enum values removed {sorted(old - new)}"))
    for c in (_bound_change(o.name, "min", o.min, n.min, lower_is_looser=True),
              _bound_change(o.name, "max", o.max, n.max, lower_is_looser=False)):
        if c:
            out.append(c)
    if o.pattern != n.pattern:
        sev = BREAKING if n.pattern is None else BREAKING if o.pattern is not None else SAFE
        out.append(Change(sev, o.name, f"pattern {o.pattern!r} -> {n.pattern!r}"
                                       + (" (can't prove it is stricter)" if o.pattern and n.pattern else "")))
    return out


def diff(old: Contract, new: Contract) -> list[Change]:
    changes = []
    for name, o in old.fields.items():
        if name not in new.fields:
            changes.append(Change(BREAKING, name, "field removed"))
        else:
            changes += _field_changes(o, new.fields[name])
    for name, n in new.fields.items():
        if name not in old.fields:
            changes.append(Change(SAFE, name, f"field added ({'required' if n.required else 'optional'})"))
    return changes


def _parse(v: str) -> tuple[int, int, int]:
    a, b, c = (int(x) for x in v.split("."))
    return a, b, c


def verdict(old: Contract, new: Contract) -> tuple[bool, list[Change], str]:
    """(ok, changes, reason). ok=False means CI should block the change."""
    changes = diff(old, new)
    ov, nv = _parse(old.version), _parse(new.version)
    breaking = [c for c in changes if c.severity == BREAKING]
    if not changes:
        return True, changes, "no schema changes"
    if nv <= ov:
        return False, changes, f"schema changed but version did not increase ({old.version} -> {new.version})"
    if breaking and nv[0] == ov[0]:
        return False, changes, (f"{len(breaking)} breaking change(s) need a major version bump "
                                f"({old.version} -> {ov[0] + 1}.0.0) and a migration plan for consumers")
    return True, changes, "ok"
