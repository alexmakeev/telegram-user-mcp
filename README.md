# telegram-user-mcp

Telegram user-account integration for MCP (Model Context Protocol), built on
[Telethon](https://github.com/LonamiWebs/Telethon). Exposes Telegram operations
(read/send messages, manage chats, etc.) to an MCP client over `stdio` or `sse`.

This is a containerized fork of [chigwell/telegram-mcp](https://github.com/chigwell/telegram-mcp).

## Image

A public image is built by CI on every push to `main` and published to GHCR:

```
ghcr.io/alexmakeev/telegram-user-mcp:latest
```

## Configuration (runtime only)

All credentials are provided at **runtime** as environment variables — nothing is
baked into the image. Obtain `TELEGRAM_API_ID` / `TELEGRAM_API_HASH` from
<https://my.telegram.org> (API development tools).

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_API_ID` | yes | Telegram API id |
| `TELEGRAM_API_HASH` | yes | Telegram API hash |
| `TELEGRAM_SESSION_NAME` | no | File-session name (default `telegram_user`) |
| `TELEGRAM_SESSION_DIR` | no | Directory for the file session (default `/app/sessions`) |
| `TELEGRAM_SESSION_STRING` | no | Portable string session (alternative to a file session) |
| `TRANSPORT` | no | `stdio` (default) or `sse` |
| `LOG_LEVEL` | no | Log level (default `INFO`) |

### Authenticating

You need either a session **string** or a session **file** for an authorized account:

- String session: `python session_string_generator.py` (interactive), then set
  `TELEGRAM_SESSION_STRING`.
- File session (QR login): `python qr_auth.py`, then mount the resulting
  `sessions/` directory into the container.

> A Telegram session grants full access to the account. **Never commit session
> files or session strings.** They are git-ignored here by default.

## Run

```bash
docker run --rm \
  -e TELEGRAM_API_ID=... \
  -e TELEGRAM_API_HASH=... \
  -e TELEGRAM_SESSION_STRING=... \
  ghcr.io/alexmakeev/telegram-user-mcp:latest
```

## License

Apache-2.0 (inherited from the upstream project). See `pyproject.toml` for authorship.
