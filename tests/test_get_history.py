import asyncio

import main

CHAT_ID = 4242
TOPIC_ID = 7


class FakeMessage:
    def __init__(self, msg_id, text):
        self.id = msg_id
        self.message = text
        self.date = "2026-10-31"
        self.reply_to = None
        self.sender = None


class StubClient:
    def __init__(self):
        self.calls = []

    async def get_entity(self, chat_id):
        return chat_id

    async def get_messages(self, entity, **kwargs):
        self.calls.append(kwargs)
        return [FakeMessage(1, "hello")]


def _run(stub, **kwargs):
    original = main.client
    main.client = stub
    try:
        return asyncio.run(main.get_history(CHAT_ID, **kwargs))
    finally:
        main.client = original


def test_topic_id_reads_only_that_topic():
    stub = StubClient()
    out = _run(stub, limit=5, topic_id=TOPIC_ID)
    assert stub.calls == [{"limit": 5, "reply_to": TOPIC_ID}]
    assert "ID: 1 |" in out


def test_without_topic_id_reads_whole_chat():
    stub = StubClient()
    _run(stub, limit=5)
    assert stub.calls == [{"limit": 5}]


def test_general_topic_one_is_forwarded():
    stub = StubClient()
    _run(stub, limit=5, topic_id=1)
    assert stub.calls == [{"limit": 5, "reply_to": 1}]


def test_invalid_topic_id_is_refused_before_any_read():
    for bad in (0, -1, True, "7"):
        stub = StubClient()
        out = _run(stub, topic_id=bad)
        assert out.startswith("Invalid topic_id")
        assert stub.calls == []
