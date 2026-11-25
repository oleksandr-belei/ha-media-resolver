"""Resolve Home Assistant media-source IDs for playback."""

from pathlib import Path
from urllib.parse import quote, unquote, urlsplit

import probatio

from homeassistant.components import media_source
from homeassistant.components.media_player import async_process_play_media_url
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

DOMAIN = "media_resolver"
SERVICE_RESOLVE = "resolve"
ATTR_MEDIA_CONTENT_ID = "media_content_id"
LOCAL_MEDIA_PREFIX = f"{media_source.URI_SCHEME}{media_source.DOMAIN}/"

CONFIG_SCHEMA = cv.empty_config_schema(DOMAIN)
RESOLVE_SCHEMA = probatio.Schema({probatio.Required(ATTR_MEDIA_CONTENT_ID): str})


def _check_local_file(path: Path, media_dir: Path) -> None:
    """Require a readable regular file inside the configured media directory."""
    try:
        root = media_dir.resolve(strict=True)
        resolved = path.resolve(strict=True)
        if not resolved.is_relative_to(root):
            raise ServiceValidationError("Local media path is outside its media directory.")
        if not resolved.is_file():
            raise ServiceValidationError("Local media path is not a regular file.")
        with resolved.open("rb"):
            pass
    except (OSError, ValueError) as err:
        raise ServiceValidationError(
            "Local media file is missing or cannot be opened."
        ) from err


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the response-only media resolver action."""

    async def resolve(call: ServiceCall) -> ServiceResponse:
        """Return a playable URL and the MIME type reported by the source."""
        media_content_id = call.data[ATTR_MEDIA_CONTENT_ID]
        if not media_source.is_media_source_id(media_content_id):
            raise ServiceValidationError("Expected a media-source:// identifier.")

        is_local = media_content_id.startswith(LOCAL_MEDIA_PREFIX)
        if is_local:
            try:
                local_id = unquote(
                    media_content_id.removeprefix(LOCAL_MEDIA_PREFIX), errors="strict"
                )
            except UnicodeDecodeError as err:
                raise ServiceValidationError("Invalid encoding in local media ID.") from err
            media_content_id = f"{LOCAL_MEDIA_PREFIX}{local_id}"

        try:
            media = await media_source.async_resolve_media(
                hass, media_content_id, target_media_player=None
            )
        except AssertionError as err:
            # Core's local source asserts that it could infer a MIME type.
            if not is_local:
                raise
            raise ServiceValidationError("Unsupported local media file type.") from err

        media_url = media.url
        if is_local:
            if (
                media.path is None
                or media.mime_type.split("/", 1)[0] not in media_source.MEDIA_MIME_TYPES
            ):
                raise ServiceValidationError("Unsupported local media file type.")
            media_dir = Path(hass.config.media_dirs[local_id.partition("/")[0]])
            await hass.async_add_executor_job(_check_local_file, media.path, media_dir)
            # The local source returns a raw path. Escape it before HA signs it.
            media_url = quote(media_url, safe="/")

        url = async_process_play_media_url(
            hass, media_url, for_supervisor_network=True
        )
        parsed = urlsplit(url)
        if parsed.scheme not in ("http", "https") or not parsed.hostname:
            raise ServiceValidationError("The media source did not return an HTTP(S) URL.")

        return {"url": url, "mime_type": media.mime_type}

    hass.services.async_register(
        DOMAIN,
        SERVICE_RESOLVE,
        resolve,
        schema=RESOLVE_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )
    return True
