"""Remove candidate artists the user already listens to."""

from collections.abc import Iterable, Sequence
from typing import Protocol, TypeVar


class Named(Protocol):
    """Anything with a read-only ``name`` string, such as a Last.fm artist model."""

    @property
    def name(self) -> str: ...


T = TypeVar("T", bound=Named)


def normalize_name(name: str) -> str:
    """Return the form used to compare artist names: trimmed and case-folded."""
    return name.strip().casefold()


def remove_known_artists(candidates: Sequence[T], known_names: Iterable[str]) -> list[T]:
    """Return the candidates the user doesn't already listen to.

    Matching is case-insensitive and ignores surrounding whitespace. Candidate order is
    preserved, duplicate candidates keep only their first occurrence, and candidates with
    blank names are dropped. The inputs are not modified.
    """
    excluded = {normalize_name(name) for name in known_names}
    excluded.discard("")

    kept: list[T] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = normalize_name(candidate.name)
        if not key or key in excluded or key in seen:
            continue
        seen.add(key)
        kept.append(candidate)
    return kept
