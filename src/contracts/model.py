"""Load a YAML data contract and turn it into a Pydantic model for runtime validation."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, create_model

TYPES = {"string": str, "integer": int, "number": float, "boolean": bool, "datetime": datetime}


@dataclass(frozen=True)
class FieldSpec:
    name: str
    type: str
    required: bool = True
    enum: tuple | None = None
    min: float | None = None
    max: float | None = None
    pattern: str | None = None


@dataclass
class Contract:
    name: str
    version: str
    owner: str
    fields: dict[str, FieldSpec] = field(default_factory=dict)

    @property
    def major(self) -> int:
        return int(self.version.split(".")[0])

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Contract":
        fields = {}
        for name, spec in d["fields"].items():
            if spec["type"] not in TYPES:
                raise ValueError(f"{name}: unknown type {spec['type']!r}")
            fields[name] = FieldSpec(name=name, type=spec["type"], required=spec.get("required", True),
                                     enum=tuple(spec["enum"]) if "enum" in spec else None,
                                     min=spec.get("min"), max=spec.get("max"), pattern=spec.get("pattern"))
        return cls(d["name"], str(d["version"]), d.get("owner", "unknown"), fields)

    @classmethod
    def load(cls, path: str | Path) -> "Contract":
        return cls.from_dict(yaml.safe_load(Path(path).read_text()))

    def to_model(self) -> type[BaseModel]:
        """Pydantic model that enforces this contract. Unknown fields are rejected."""
        defs = {}
        for f in self.fields.values():
            py = Literal.__getitem__(f.enum) if f.enum else TYPES[f.type]
            kwargs = {k: v for k, v in (("ge", f.min), ("le", f.max), ("pattern", f.pattern)) if v is not None}
            if f.required:
                defs[f.name] = (py, Field(..., **kwargs))
            else:
                defs[f.name] = (Optional[py], Field(None, **kwargs))
        return create_model(f"{self.name.title()}V{self.major}", __config__=ConfigDict(extra="forbid", strict=False), **defs)
