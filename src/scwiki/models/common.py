from __future__ import annotations

from dataclasses import dataclass

from scwiki.models.base import Value


@dataclass(frozen=True)
class ManufacturerRef(Value):
    name: str | None = None
    code: str | None = None
    uuid: str | None = None
    link: str | None = None


@dataclass(frozen=True)
class Dimension(Value):
    length: float | None = None
    width: float | None = None
    height: float | None = None


@dataclass(frozen=True)
class Crew(Value):
    min: int | None = None
    max: int | None = None


@dataclass(frozen=True)
class Speed(Value):
    scm: float | None = None
    max: float | None = None
    boost_forward: float | None = None
    boost_backward: float | None = None


@dataclass(frozen=True)
class Shield(Value):
    hp: float | None = None
    regeneration: float | None = None
    face_type: str | None = None


@dataclass(frozen=True)
class Signature(Value):
    ir_quantum: float | None = None
    ir_shields: float | None = None
    em_quantum: float | None = None
    em_shields: float | None = None


@dataclass(frozen=True)
class Image(Value):
    source: str | None = None
    original_url: str | None = None


@dataclass(frozen=True)
class Named(Value):
    id: str | int | None = None
    name: str | None = None
