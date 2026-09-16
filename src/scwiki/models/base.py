"""Model base class and payload helpers.

Models type the fields most callers need and keep the untouched payload in
``raw`` so a new API field is reachable before the model catches up.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field, fields
from typing import Any, ClassVar, TypeVar

M = TypeVar("M", bound="Model")
V = TypeVar("V", bound="Value")

DEFAULT_LOCALE = "en_EN"


@dataclass(frozen=True)
class ResultMeta:
    version: str | None = None
    processed_at: str | None = None
    cached: bool = False
    stale: bool = False
    fetched_at: float = 0.0


def localized(value: Any, locale: str = DEFAULT_LOCALE) -> str | None:
    """Collapse the API's ``{"en_EN": ...}`` translation maps to one string."""
    if value is None or isinstance(value, str):
        return value
    if isinstance(value, Mapping):
        if locale in value:
            return str(value[locale])
        for candidate in value.values():
            if isinstance(candidate, str):
                return candidate
    return None


def _as_float(value: Any) -> float | None:
    return None if value is None else float(value)


def _as_int(value: Any) -> int | None:
    return None if value is None else int(value)


@dataclass(frozen=True)
class Value:
    """Nested value object built from a sub-mapping."""

    raw: Mapping[str, Any] = field(default_factory=dict, repr=False, compare=False)

    @classmethod
    def from_payload(cls: type[V], data: Mapping[str, Any] | None) -> V | None:
        if not isinstance(data, Mapping):
            return None
        return cls(raw=data, **cls._pick(data))

    @classmethod
    def _pick(cls, data: Mapping[str, Any]) -> dict[str, Any]:
        return {f.name: data.get(f.name) for f in fields(cls) if f.name != "raw" and f.init}


def sub_list(cls: type[V], data: Any) -> tuple[V, ...]:
    if not isinstance(data, Sequence) or isinstance(data, str):
        return ()
    out = []
    for item in data:
        built = cls.from_payload(item)
        if built is not None:
            out.append(built)
    return tuple(out)


@dataclass(frozen=True)
class Model:
    """Top-level resource. Subclasses declare typed fields and a ``_derive`` map."""

    raw: Mapping[str, Any] = field(default_factory=dict, repr=False, compare=False)
    meta: ResultMeta = field(default_factory=ResultMeta, repr=False, compare=False)

    _derive: ClassVar[Mapping[str, Callable[[Mapping[str, Any]], Any]]] = {}

    @classmethod
    def from_payload(cls: type[M], data: Mapping[str, Any], meta: ResultMeta | None = None) -> M:
        values: dict[str, Any] = {}
        for f in fields(cls):
            if f.name in ("raw", "meta") or not f.init:
                continue
            derive = cls._derive.get(f.name)
            values[f.name] = derive(data) if derive is not None else data.get(f.name)
        return cls(raw=data, meta=meta or ResultMeta(), **values)


def text(key: str) -> Callable[[Mapping[str, Any]], str | None]:
    return lambda data: localized(data.get(key))


def nested(key: str, cls: type[V]) -> Callable[[Mapping[str, Any]], V | None]:
    return lambda data: cls.from_payload(data.get(key))


def nested_list(key: str, cls: type[V]) -> Callable[[Mapping[str, Any]], tuple[V, ...]]:
    return lambda data: sub_list(cls, data.get(key))


def as_float(key: str) -> Callable[[Mapping[str, Any]], float | None]:
    return lambda data: _as_float(data.get(key))


def as_int(key: str) -> Callable[[Mapping[str, Any]], int | None]:
    return lambda data: _as_int(data.get(key))
