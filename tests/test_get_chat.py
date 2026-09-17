"""Offline regression tests for the `get_chat` MCP tool.

Bug (observed in production, twice): `get_chat` reported a "Last Message" and
"Unread" belonging to a DIFFERENT chat than the one requested — it echoed the
globally most-recent dialog (often the caller's own active topic) instead of the
target peer. Root cause: it used

    client.get_dialogs(limit=1, offset_id=0, offset_peer=entity)

believing `offset_peer` filters to `entity`. In Telethon `offset_peer` is a
PAGINATION CURSOR, not a filter, so with `offset_id=0`/no `offset_date` it returns
the single top dialog of the whole dialog list — an unrelated chat.

These tests are fully offline: the Telethon client is replaced by a stub whose
`get_dialogs()` deliberately returns a WRONG chat, while the correct per-peer
lookup (`GetPeerDialogsRequest` + `get_messages(entity, ...)`) returns the target
chat. The old code path therefore surfaces the wrong chat (RED); the fixed code
path surfaces the target chat (GREEN).
"""

import asyncio
from datetime import datetime

from telethon import functions
from telethon.tl.types import User

import main


# --- Lightweight fakes (no network, no real Telethon session) -----------------


class FakeSender:
    def __init__(self, first_name, last_name=None, title=None):
        self.first_name = first_name
        self.last_name = last_name
        if title is not None:
            self.title = title


class FakeMessage:
    def __init__(self, msg_id, text, sender, date=None):
        self.id = msg_id
        self.message = text
        self.sender = sender
        self.date = date or datetime(2026, 9, 17, 12, 0, 0)


class FakeDialog:
    def __init__(self, unread_count, top_message=None, message=None):
        self.unread_count = unread_count
        self.top_message = top_message
        # `.message` is what the OLD (buggy) get_dialogs path reads.
        self.message = message


class FakePeerDialogs:
    def __init__(self, dialogs, messages=None):
        self.dialogs = dialogs
        self.messages = messages or []
        self.users = []
        self.chats = []


# Target peer the caller asked about + its REAL last message / unread.
TARGET_ID = 4242
TARGET_TOP_MSG_ID = 555
TARGET_LAST_TEXT = "hi from the target chat"
TARGET_UNREAD = 3

# The unrelated dialog that a raw get_dialogs(limit=1, offset_peer=...) returns:
# in production this was the caller's own active topic — hence the "echo".
WRONG_LAST_TEXT = "Анализ статуса mw32-acpz"  # caller's own task text
WRONG_UNREAD = 2300


class StubClient:
    """Stub Telethon client distinguishing the buggy vs the correct code path.

    - get_dialogs(...)  -> the WRONG (globally-top) dialog  [old buggy path]
    - client(GetPeerDialogsRequest) -> the TARGET peer's dialog  [fixed path]
    - get_messages(entity, ids=...) -> the TARGET peer's last message  [fixed path]
    """

    def __init__(self):
        self.get_dialogs_called = False
        self.peer_dialogs_requests = []
        self.get_messages_calls = []
        self._target_entity = User(id=TARGET_ID, first_name="TargetUser")
        self._wrong_dialog = FakeDialog(
            unread_count=WRONG_UNREAD,
            message=FakeMessage(999, WRONG_LAST_TEXT, FakeSender("SomeOtherChat")),
        )
        self._target_msg = FakeMessage(
            TARGET_TOP_MSG_ID, TARGET_LAST_TEXT, FakeSender("TargetUser")
        )

    async def get_entity(self, chat_id):
        return self._target_entity

    async def get_participants(self, entity, limit=0):
        class _R(list):
            total = 0

        return _R()

    async def get_dialogs(self, *args, **kwargs):
        # Old buggy path lands here and gets an UNRELATED chat.
        self.get_dialogs_called = True
        return [self._wrong_dialog]

    async def get_messages(self, entity, ids=None, **kwargs):
        self.get_messages_calls.append((entity, ids))
        if ids == TARGET_TOP_MSG_ID:
            return self._target_msg
        return None

    async def __call__(self, request):
        # Fixed path: resolve the dialog for the EXACT peer.
        self.peer_dialogs_requests.append(request)
        target_dialog = FakeDialog(
            unread_count=TARGET_UNREAD, top_message=TARGET_TOP_MSG_ID
        )
        return FakePeerDialogs(dialogs=[target_dialog])


def _run_get_chat(monkeyless_client):
    """Swap in the stub client, call get_chat, restore the real client."""
    original = main.client
    main.client = monkeyless_client
    try:
        return asyncio.run(main.get_chat(TARGET_ID))
    finally:
        main.client = original


def test_get_chat_returns_target_peer_last_message_and_unread():
    """get_chat must report the TARGET chat's real last message + unread,
    never an unrelated (globally-top) chat's."""
    stub = StubClient()
    out = _run_get_chat(stub)

    # Correct data for the requested peer is present.
    assert TARGET_LAST_TEXT in out, out
    assert f"Unread Messages: {TARGET_UNREAD}" in out, out

    # The unrelated chat's data must NOT leak in (the original bug).
    assert WRONG_LAST_TEXT not in out, out
    assert str(WRONG_UNREAD) not in out, out


def test_get_chat_uses_per_peer_lookup_not_pagination():
    """The fix must query the exact peer via GetPeerDialogsRequest and must NOT
    use the get_dialogs pagination hack (offset_peer is not a filter)."""
    stub = StubClient()
    _run_get_chat(stub)

    # Per-peer dialog lookup was used, for the target entity.
    assert stub.peer_dialogs_requests, "GetPeerDialogsRequest was never issued"
    req = stub.peer_dialogs_requests[0]
    assert isinstance(req, functions.messages.GetPeerDialogsRequest), type(req)
    assert any(getattr(p, "id", None) == TARGET_ID for p in req.peers), req.peers

    # Last message fetched for the target peer via the proven get_messages path.
    assert (stub._target_entity, TARGET_TOP_MSG_ID) in stub.get_messages_calls

    # The buggy global-pagination path must no longer be used.
    assert not stub.get_dialogs_called, "get_dialogs pagination hack still used"
