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
