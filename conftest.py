"""Pytest bootstrap for the telegram-user MCP server.

`main.py` runs real work at import time — a deploy guard, config parsing from the
environment and a Telethon client/session bootstrap. Tests are fully OFFLINE and
ISOLATED: we pin the required environment BEFORE `main` is imported anywhere, and
neutralise `main.py`'s `load_dotenv(override=True)` so a stray `.env` up the tree
(or a real value already in the shell env) can never select a real Telegram
session/credentials during a test import. The Telethon client itself is
monkeypatched per-test (see tests/test_get_chat.py); nothing here connects.
"""

import os
import tempfile

# Deterministic, isolated env for the offline import of main.py.
# Explicit assignment (NOT setdefault): a real value already present in the
# environment must not leak into the test import and select a real session.
os.environ["DEPLOY_CONFIRMED_BY_ADMIN"] = "yes"
os.environ["TELEGRAM_API_ID"] = "12345"
os.environ["TELEGRAM_API_HASH"] = "0123456789abcdef0123456789abcdef"
# Throwaway session dir so the file-based session bootstrap stays offline and never
# writes into the repo or a real sessions/ volume.
os.environ["TELEGRAM_SESSION_DIR"] = tempfile.mkdtemp(prefix="tg-user-mcp-test-sess-")
os.environ["TELEGRAM_SESSION_NAME"] = "test_session"
# Never let a real StringSession be picked up from the shell env.
os.environ.pop("TELEGRAM_SESSION_STRING", None)

# main.py calls `load_dotenv(override=True)` at import time, which searches UP the
# directory tree for a `.env` and would OVERRIDE the values above with real creds or
# a real session path. Replace it with a no-op before main is imported so the import
# stays fully offline and isolated. `main` does `from dotenv import load_dotenv`, so
# patching the attribute on the module here (before main's import) is what it binds.
import dotenv  # noqa: E402

dotenv.load_dotenv = lambda *args, **kwargs: False
