from collections.abc import Callable
from typing import Any
from urllib.parse import parse_qs, urlparse

import pytest
import requests
import responses

from discover.lastfm import (
    API_URL,
    USER_AGENT,
    ArtistNotFoundError,
    InvalidApiKeyError,
    LastFmClient,
    LastFmError,
    LastFmTimeoutError,
    UserNotFoundError,
    parse_similar_artists,
    parse_top_artists,
    parse_top_tags,
)

API_KEY = "secret-test-key-123"
Loader = Callable[[str], dict[str, Any]]


@pytest.fixture
def client() -> LastFmClient:
    return LastFmClient(API_KEY)


def sent_params() -> dict[str, str]:
    """Query parameters of the single request made during the test."""
    assert len(responses.calls) == 1
    query = parse_qs(urlparse(responses.calls[0].request.url).query)
    return {key: values[0] for key, values in query.items()}


# --- Parsing ----------------------------------------------------------------


def test_parse_similar_artists(load_fixture: Loader) -> None:
    artists = parse_similar_artists(load_fixture("similar_artists.json"))
    assert [a.name for a in artists] == ["Sonny & Cher", "Madonna", "Kylie Minogue"]
    assert [a.match for a in artists] == [1.0, 0.62, 0.5873]


def test_parse_similar_artists_single_object_becomes_list() -> None:
    data = {"similarartists": {"artist": {"name": "Sonny & Cher", "match": "1"}}}
    artists = parse_similar_artists(data)
    assert [(a.name, a.match) for a in artists] == [("Sonny & Cher", 1.0)]


@pytest.mark.parametrize(
    "data",
    [
        {"similarartists": {"artist": [], "@attr": {"artist": "Cher"}}},
        {"similarartists": {"@attr": {"artist": "Cher"}}},
        {},
    ],
)
def test_parse_similar_artists_empty(data: dict[str, Any]) -> None:
    assert parse_similar_artists(data) == []


def test_parse_top_artists(load_fixture: Loader) -> None:
    artists = parse_top_artists(load_fixture("top_artists.json"))
    assert [(a.name, a.playcount, a.rank) for a in artists] == [
        ("Radiohead", 1452, 1),
        ("Portishead", 873, 2),
        ("Björk", 610, 3),
    ]


def test_parse_top_tags(load_fixture: Loader) -> None:
    tags = parse_top_tags(load_fixture("top_tags.json"))
    assert [(t.name, t.count) for t in tags] == [
        ("pop", 100),
        ("female vocalists", 61),
        ("dance", 38),
    ]


def test_parse_top_tags_empty() -> None:
    assert parse_top_tags({"toptags": {"tag": [], "@attr": {"artist": "Cher"}}}) == []


def test_parse_malformed_item_raises_lastfm_error() -> None:
    with pytest.raises(LastFmError, match="unexpected format"):
        parse_similar_artists({"similarartists": {"artist": [{"name": "Cher", "match": "n/a"}]}})


# --- Requests ---------------------------------------------------------------


@responses.activate
def test_get_similar_artists_request(client: LastFmClient, load_fixture: Loader) -> None:
    responses.get(API_URL, json=load_fixture("similar_artists.json"))

    artists = client.get_similar_artists("Cher")

    assert artists[0].name == "Sonny & Cher"
    assert sent_params() == {
        "method": "artist.getSimilar",
        "artist": "Cher",
        "limit": "30",
        "autocorrect": "1",
        "api_key": API_KEY,
        "format": "json",
    }
    assert responses.calls[0].request.headers["User-Agent"] == USER_AGENT


@responses.activate
def test_get_user_top_artists_request(client: LastFmClient, load_fixture: Loader) -> None:
    responses.get(API_URL, json=load_fixture("top_artists.json"))

    artists = client.get_user_top_artists("rj")

    assert len(artists) == 3
    params = sent_params()
    assert params["method"] == "user.getTopArtists"
    assert params["user"] == "rj"
    assert params["period"] == "overall"
    assert params["limit"] == "200"


@responses.activate
def test_get_top_tags_request(client: LastFmClient, load_fixture: Loader) -> None:
    responses.get(API_URL, json=load_fixture("top_tags.json"))

    tags = client.get_top_tags("Cher")

    assert tags[0].name == "pop"
    params = sent_params()
    assert params["method"] == "artist.getTopTags"
    assert params["artist"] == "Cher"
    assert params["autocorrect"] == "1"


# --- Errors -----------------------------------------------------------------


@responses.activate
def test_unknown_artist_on_similar(client: LastFmClient, load_fixture: Loader) -> None:
    responses.get(API_URL, json=load_fixture("error_6_artist.json"))
    with pytest.raises(ArtistNotFoundError, match="Frnk Ocean") as exc_info:
        client.get_similar_artists("Frnk Ocean")
    assert exc_info.value.code == 6


@responses.activate
def test_unknown_artist_on_top_tags(client: LastFmClient, load_fixture: Loader) -> None:
    responses.get(API_URL, json=load_fixture("error_6_artist.json"))
    with pytest.raises(ArtistNotFoundError):
        client.get_top_tags("Frnk Ocean")


@responses.activate
def test_unknown_user(client: LastFmClient, load_fixture: Loader) -> None:
    responses.get(API_URL, json=load_fixture("error_6_user.json"))
    with pytest.raises(UserNotFoundError, match="nobody_here"):
        client.get_user_top_artists("nobody_here")


@pytest.mark.parametrize("status", [200, 403])
@responses.activate
def test_invalid_api_key(client: LastFmClient, load_fixture: Loader, status: int) -> None:
    responses.get(API_URL, json=load_fixture("error_10.json"), status=status)
    with pytest.raises(InvalidApiKeyError, match="LASTFM_API_KEY") as exc_info:
        client.get_similar_artists("Cher")
    assert exc_info.value.code == 10


@responses.activate
def test_other_error_code(client: LastFmClient) -> None:
    responses.get(API_URL, json={"error": 29, "message": "Rate limit exceeded"}, status=429)
    with pytest.raises(LastFmError, match="Rate limit exceeded") as exc_info:
        client.get_similar_artists("Cher")
    assert exc_info.value.code == 29


@responses.activate
def test_timeout(client: LastFmClient) -> None:
    responses.get(API_URL, body=requests.Timeout())
    with pytest.raises(LastFmTimeoutError, match="10 seconds"):
        client.get_similar_artists("Cher")


@responses.activate
def test_connection_error(client: LastFmClient) -> None:
    responses.get(API_URL, body=requests.ConnectionError())
    with pytest.raises(LastFmError, match="Couldn't reach Last.fm"):
        client.get_similar_artists("Cher")


@responses.activate
def test_non_json_server_error(client: LastFmClient) -> None:
    responses.get(API_URL, body="<html>Internal Server Error</html>", status=500)
    with pytest.raises(LastFmError, match="HTTP 500"):
        client.get_similar_artists("Cher")


@pytest.mark.parametrize(
    "mock",
    [
        {"json": {"error": 6, "message": "not found"}},
        {"json": {"error": 10, "message": "bad key"}},
        {"json": {"error": 29, "message": "slow down"}},
        {"body": requests.Timeout(f"timed out: {API_URL}?api_key={API_KEY}")},
        {"body": requests.ConnectionError(f"failed: {API_URL}?api_key={API_KEY}")},
        {"body": "not json", "status": 500},
    ],
)
@responses.activate
def test_api_key_never_in_error_message(client: LastFmClient, mock: dict[str, Any]) -> None:
    responses.get(API_URL, **mock)
    with pytest.raises(LastFmError) as exc_info:
        client.get_similar_artists("Cher")
    assert API_KEY not in str(exc_info.value)
