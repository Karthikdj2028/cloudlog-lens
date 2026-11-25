"""Structural contracts for mapper and reducer callables."""
from __future__ import annotations
from collections.abc import Iterable, Iterator
from typing import Protocol, TypeVar
TIn = TypeVar("TIn", contravariant=True)
K = TypeVar("K")
V = TypeVar("V")
TOut = TypeVar("TOut")

class Mapper(Protocol[TIn, K, V]):
    def __call__(self, record: TIn) -> Iterable[tuple[K, V]]: ...

class Reducer(Protocol[K, V, TOut]):
    def __call__(self, key: K, values: Iterator[V]) -> Iterable[TOut]: ...
