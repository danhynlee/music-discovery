from dataclasses import dataclass

import pytest

from discover.filter import normalize_name, remove_known_artists


@dataclass(frozen=True)
class Artist:
    name: str
    match: float


def names(artists: list[Artist]) -> list[str]:
    return [a.name for a in artists]


def test_normalize_name_trims_and_lowercases() -> None:
    assert normalize_name("  RadioHead \t") == "radiohead"


def test_empty_candidates() -> None:
    assert remove_known_artists([], ["Radiohead"]) == []


def test_empty_known_names_returns_all_candidates_in_order() -> None:
    candidates = [Artist("Bon Iver", 0.9), Artist("James Blake", 0.8)]
    assert remove_known_artists(candidates, []) == candidates


def test_both_empty() -> None:
    assert remove_known_artists([], []) == []


@pytest.mark.parametrize("known", ["RADIOHEAD", "radiohead", "RaDiOhEaD"])
def test_different_capitalization_is_removed(known: str) -> None:
    candidates = [Artist("Radiohead", 0.9), Artist("Portishead", 0.7)]
    assert names(remove_known_artists(candidates, [known])) == ["Portishead"]


def test_whitespace_on_either_side_is_ignored() -> None:
    candidates = [Artist("Radiohead\n", 0.9), Artist("Portishead", 0.7)]
    assert names(remove_known_artists(candidates, ["  radiohead "])) == ["Portishead"]


def test_duplicate_candidates_keep_first_occurrence() -> None:
    first = Artist("SZA", 0.9)
    candidates = [first, Artist(" sza ", 0.5), Artist("Solange", 0.8), Artist("SZA", 0.4)]
    result = remove_known_artists(candidates, [])
    assert result == [first, Artist("Solange", 0.8)]
    assert result[0].match == 0.9


def test_duplicate_known_names() -> None:
    candidates = [Artist("Radiohead", 0.9), Artist("Portishead", 0.7)]
    result = remove_known_artists(candidates, ["Radiohead", "radiohead", "Radiohead"])
    assert names(result) == ["Portishead"]


def test_order_is_preserved() -> None:
    candidates = [Artist(n, 1.0 - i / 10) for i, n in enumerate(["A", "B", "C", "D", "E"])]
    assert names(remove_known_artists(candidates, ["b", "d"])) == ["A", "C", "E"]


def test_inputs_are_not_mutated() -> None:
    candidates = [Artist("Radiohead", 0.9), Artist("Portishead", 0.7)]
    known = ["radiohead"]
    candidates_before, known_before = list(candidates), list(known)
    remove_known_artists(candidates, known)
    assert candidates == candidates_before
    assert known == known_before


@pytest.mark.parametrize("blank", ["", "   ", "\t\n"])
def test_blank_candidate_names_are_dropped(blank: str) -> None:
    candidates = [Artist(blank, 0.9), Artist("Portishead", 0.7)]
    assert names(remove_known_artists(candidates, [])) == ["Portishead"]


def test_blank_known_names_are_ignored() -> None:
    candidates = [Artist("Portishead", 0.7)]
    assert remove_known_artists(candidates, ["", "  "]) == candidates


def test_non_ascii_capitalization_is_removed() -> None:
    candidates = [Artist("Sigur Rós", 0.9), Artist("Múm", 0.6)]
    assert names(remove_known_artists(candidates, ["SIGUR RÓS"])) == ["Múm"]
