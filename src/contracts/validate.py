"""Validate a batch of records against a contract: split into valid and rejected, summarise why."""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from pydantic import ValidationError

from .model import Contract


@dataclass
class BatchReport:
    total: int = 0
    valid: list[dict] = field(default_factory=list)
    rejected: list[tuple[dict, list[str]]] = field(default_factory=list)
    reasons: Counter = field(default_factory=Counter)

    @property
    def reject_rate(self) -> float:
        return len(self.rejected) / self.total if self.total else 0.0


def validate_batch(contract: Contract, records: list[dict]) -> BatchReport:
    model = contract.to_model()
    rep = BatchReport(total=len(records))
    for rec in records:
        try:
            rep.valid.append(model.model_validate(rec).model_dump())
        except ValidationError as e:
            errs = [f"{'.'.join(map(str, err['loc'])) or '(record)'}: {err['type']}" for err in e.errors()]
            rep.rejected.append((rec, errs))
            rep.reasons.update(errs)
    return rep
