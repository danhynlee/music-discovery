"""Last.fm API client: similar artists, user top artists, and top tags."""

from typing import Any

import requests
from pydantic import AliasPath, BaseModel, ConfigDict, Field, ValidationError

from discover import __version__

API_URL = "https://ws.audioscrobbler.com/2.0/"
USER_AGENT = f"music-discovery/{__version__} (Python requests)"

ERROR_INVALID_PARAMETERS = 6
ERROR_INVALID_API_KEY = 10


# --- Models -----------------------------------------------------------------


class _LastFmModel(BaseModel):
    model_config = ConfigDict(extra="ignore", frozen=True)


class SimilarArtist(_LastFmModel):
    name: str
    match: float


class TopArtist(_LastFmModel):
    name: str
    playcount: int
    rank: int = Field(validation_alias=AliasPath("@attr", "rank"))


class Tag(_LastFmModel):
    name: str
    count: int


# --- Errors -----------------------------------------------------------------


class LastFmError(Exception):
    """A Last.fm request failed. The message is safe to show to the user."""

    def __init__(self, message: str, code: int | None = None) -> None:
        super().__init__(message)
        self.code = code


class _NotFoundError(LastFmError):
    kind = "item"

    def __init__(self, subject: str) -> None:
        super().__init__(f"Last.fm has no {self.kind} named {subject!r}.", ERROR_INVALID_PARAMETERS)
        self.subject = subject


class ArtistNotFoundError(_NotFoundError):
    kind = "artist"


class UserNotFoundError(_NotFoundError):
    kind = "user"


class InvalidApiKeyError(LastFmError):
    def __init__(self) -> None:
        super().__init__(
            "Last.fm rejected the API key. Check LASTFM_API_KEY in .env.", ERROR_INVALID_API_KEY
        )


class LastFmTimeoutError(LastFmError):
    def __init__(self, timeout: float) -> None:
        super().__init__(f"Last.fm didn't respond within {timeout:g} seconds.")


# --- Parsing ----------------------------------------------------------------


def _as_list(value: Any) -> list[Any]:
    """Last.fm sends a lone result as an object and may omit empty lists entirely."""
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _parse_items(model: type[_LastFmModel], items: Any) -> list[Any]:
    try:
        return [model.model_validate(item) for item in _as_list(items)]
    except ValidationError as exc:
        raise LastFmError("Last.fm returned a response in an unexpected format.") from exc


def parse_similar_artists(data: dict[str, Any]) -> list[SimilarArtist]:
    return _parse_items(SimilarArtist, data.get("similarartists", {}).get("artist"))


def parse_top_artists(data: dict[str, Any]) -> list[TopArtist]:
    return _parse_items(TopArtist, data.get("topartists", {}).get("artist"))


def parse_top_tags(data: dict[str, Any]) -> list[Tag]:
    return _parse_items(Tag, data.get("toptags", {}).get("tag"))


def raise_for_error(data: dict[str, Any], not_found: type[_NotFoundError], subject: str) -> None:
    """Raise the matching LastFmError if the response body is a Last.fm error."""
    if "error" not in data:
        return
    code = data["error"]
    if code == ERROR_INVALID_PARAMETERS:
        raise not_found(subject)
    if code == ERROR_INVALID_API_KEY:
        raise InvalidApiKeyError()
    message = data.get("message") or "unknown error"
    raise LastFmError(f"Last.fm error {code}: {message}", code)


# --- Client -----------------------------------------------------------------


class LastFmClient:
    def __init__(
        self,
        api_key: str,
        *,
        session: requests.Session | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._api_key = api_key
        self._session = session or requests.Session()
        self._timeout = timeout

    def get_similar_artists(self, artist: str, limit: int = 30) -> list[SimilarArtist]:
        params = {"method": "artist.getSimilar", "artist": artist, "limit": limit, "autocorrect": 1}
        return parse_similar_artists(self._get(params, ArtistNotFoundError, artist))

    def get_user_top_artists(self, user: str, limit: int = 200) -> list[TopArtist]:
        params = {"method": "user.getTopArtists", "user": user, "period": "overall", "limit": limit}
        return parse_top_artists(self._get(params, UserNotFoundError, user))

    def get_top_tags(self, artist: str) -> list[Tag]:
        params = {"method": "artist.getTopTags", "artist": artist, "autocorrect": 1}
        return parse_top_tags(self._get(params, ArtistNotFoundError, artist))

    def _get(
        self,
        params: dict[str, str | int],
        not_found: type[_NotFoundError],
        subject: str,
    ) -> dict[str, Any]:
        query = {**params, "api_key": self._api_key, "format": "json"}
        try:
            response = self._session.get(
                API_URL,
                params=query,
                headers={"User-Agent": USER_AGENT},
                timeout=self._timeout,
            )
        except requests.Timeout as exc:
            raise LastFmTimeoutError(self._timeout) from exc
        except requests.RequestException as exc:
            # Don't include str(exc): it can contain the request URL, and with it the API key.
            raise LastFmError(f"Couldn't reach Last.fm ({type(exc).__name__}).") from exc

        try:
            data = response.json()
        except ValueError:
            data = None
        if not isinstance(data, dict):
            raise LastFmError(
                f"Last.fm returned an unreadable response (HTTP {response.status_code})."
            )

        raise_for_error(data, not_found, subject)
        if not response.ok:
            raise LastFmError(f"Last.fm request failed (HTTP {response.status_code}).")
        return data
