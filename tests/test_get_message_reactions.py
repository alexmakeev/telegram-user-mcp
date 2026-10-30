"""Offline tests for the `get_message_reactions` MCP tool.

Counts come from the message itself (`message.reactions.results`); the
who-reacted list (`GetMessageReactionsListRequest`) is an optional enrichment
that Telegram may refuse (e.g. MsgIdInvalidError).
"""

import asyncio
import json
from datetime import datetime

from telethon import functions
from telethon.errors import MsgIdInvalidError
from telethon.tl.types import (
    MessagePeerReaction,
    MessageReactions,
    PeerUser,
    ReactionCount,
    ReactionEmoji,
)

import main

CHAT_ID = 4242
MSG_ID = 77


class FakeMessage:
    def __init__(self, reactions):
        self.id = MSG_ID
        self.reactions = reactions


class StubClient:
    def __init__(self, message, list_result=None, list_error=None):
        self._message = message
        self._list_result = list_result
        self._list_error = list_error

    async def get_input_entity(self, chat_id):
        return chat_id

    async def get_messages(self, entity, ids):
        assert ids == MSG_ID
        return self._message

    async def __call__(self, request):
        assert isinstance(request, functions.messages.GetMessageReactionsListRequest)
        if self._list_error is not None:
            raise self._list_error
        return self._list_result


def _run(stub):
    original = main.client
    main.client = stub
    try:
        return asyncio.run(main.get_message_reactions(CHAT_ID, MSG_ID))
    finally:
        main.client = original


def _broken_heart_message():
    return FakeMessage(
        MessageReactions(results=[ReactionCount(reaction=ReactionEmoji("💔"), count=1)])
    )


def test_counts_returned_when_who_reacted_list_refused():
    out = _run(StubClient(_broken_heart_message(), list_error=MsgIdInvalidError(request=None)))
    assert "GEN-ERR" not in out, out
    data = json.loads(out)
    assert data["counts"] == {"💔": 1}, data
    assert "reactors" not in data, data
    assert "MsgIdInvalidError" in data["reactors_unavailable"], data


def test_counts_and_reactors_when_list_available():
    list_result = type("R", (), {})()
    list_result.reactions = [
        MessagePeerReaction(
            peer_id=PeerUser(user_id=9),
            date=datetime(2026, 10, 30, 12, 0, 0),
            reaction=ReactionEmoji("💔"),
        )
    ]
    out = _run(StubClient(_broken_heart_message(), list_result=list_result))
    data = json.loads(out)
    assert data["counts"] == {"💔": 1}
    assert data["reactors"] == [
        {"user_id": 9, "emoji": "💔", "date": "2026-10-30T12:00:00"}
    ]
    assert "reactors_unavailable" not in data


def test_no_reactions_on_message_is_stated():
    out = _run(StubClient(FakeMessage(None), list_error=AssertionError("must not be called")))
    assert out == f"No reactions on message {MSG_ID} in chat {CHAT_ID}."


def test_missing_message_is_stated():
    out = _run(StubClient(None))
    assert out == f"Message {MSG_ID} not found in chat {CHAT_ID}."
