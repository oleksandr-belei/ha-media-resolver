# Media Resolver for Home Assistant

Turn a Home Assistant `media-source://` identifier into an absolute HTTP(S) URL and a MIME type. Use the result in a script, automation, or Music Assistant announcement.

## Installation

The integration has been exercised on Home Assistant Core **2026.11.2**. Compatibility with older versions has yet to be established.

### HACS custom repository

1. In HACS, open **Custom repositories** from the menu.
2. Paste this repository’s GitHub URL, choose **Integration**, and add it.
3. Find **Media Resolver** and select **Download**.
4. Complete the activation steps below.

### Manual installation

1. Download the source for the desired release.
2. Copy `custom_components/media_resolver/` into `custom_components/` inside your Home Assistant configuration directory.
3. Complete the activation steps below.

### Activation

Add the following top-level entry to `configuration.yaml`, check the configuration, then restart Home Assistant.

```yaml
media_resolver:
```

Look for `media_resolver.resolve` in the Home Assistant action picker.

## Action reference

`media_resolver.resolve` is a response-only action. Use `response_variable` to capture its response in a script or automation.

| Direction | Field | Type | Meaning |
| --- | --- | --- | --- |
| Input | `media_content_id` | string, required | A Home Assistant `media-source://` identifier. |
| Output | `url` | string | Absolute HTTP(S) URL prepared by Home Assistant for playback. |
| Output | `mime_type` | string | Media type reported by the source, such as `audio/mpeg`. |

## Examples

Paste the `sequence` into a Home Assistant script. Replace the example TTS provider, language, file, and speaker with values from your setup.

### Resolve text-to-speech

```yaml
sequence:
  - variables:
      message: "Dinner is ready."
      language: en_US
  - action: media_resolver.resolve
    data:
      media_content_id: >-
        media-source://tts/tts.piper?message={{ message | urlencode }}&language={{ language | urlencode }}&cache=true
    response_variable: speech
  - stop: Speech URL resolved
    response_variable: speech
```

For a provider that accepts voice options, append `&tts_options={{ {'voice': 'example_voice'} | to_json | urlencode }}` and substitute a supported voice. Home Assistant’s TTS provider handles language, options, and caching.

### Play a Music Assistant announcement with a local intro

Put `intro.mp3` in Home Assistant’s configured `local` media directory. For a nested file, use an ID such as `media-source://media_source/local/sounds/intro.mp3`.

```yaml
sequence:
  - action: media_resolver.resolve
    data:
      media_content_id: media-source://media_source/local/intro.mp3
    response_variable: intro
  - action: media_resolver.resolve
    data:
      media_content_id: >-
        media-source://tts/tts.piper?message=Dinner%20is%20ready.&cache=true
    response_variable: speech
  - action: music_assistant.play_announcement
    target:
      entity_id: media_player.kitchen_speaker
    data:
      url: "{{ speech.url }}"
      use_pre_announce: true
      pre_announce_url: "{{ intro.url }}"
```

This sequence stops if the intro fails to resolve. For an optional intro, add `continue_on_error: true` to its resolver step and branch on whether `intro` is defined. In the fallback branch, call `music_assistant.play_announcement` with `speech.url` and `use_pre_announce: false`.

## Errors and limits

| Condition | Behavior |
| --- | --- |
| Invalid media-source ID or a source that returns no absolute HTTP(S) URL | The action fails without a response value. |
| Missing or unreadable local file | The action fails with `Local media file is missing or cannot be opened.` |
| Local directory, unsupported media type, invalid path, or path outside its media directory | The action fails. |
| Unknown source, unavailable TTS provider, or rejected provider options | The underlying Home Assistant error propagates. |

- Local validation checks that the resolved path points to a readable regular file inside its configured media directory. It supports nested paths and URL-encoded names and performs the file check without an HTTP request. MIME detection does not verify the file’s audio or video contents.
- Home Assistant handles URL selection and signing. A Music Assistant server or other consumer must be able to reach the returned hostname. Use signed media URLs and temporary TTS URLs promptly, and treat them as sensitive while valid.
- Success means the source produced a URL. Playback, network access, codec support, and successful TTS generation when the URL is fetched depend on the source and consumer. Some media sources require a specific target player. This action resolves without one.

## Repository layout

```text
.
├── README.md
├── LICENSE
├── hacs.json
└── custom_components/
    └── media_resolver/
        ├── __init__.py
        ├── manifest.json
        ├── services.yaml
        └── brand/
            └── icon.png
```

## License

MIT. See [LICENSE](LICENSE).
