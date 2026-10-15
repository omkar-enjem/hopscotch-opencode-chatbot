"""End-to-end agent loop tests with a mocked LLM (no API key required)."""

from __future__ import annotations

import app.router as router


def _final(content: str) -> dict:
    return {"role": "assistant", "content": content, "_model": "mock/model"}


def _tool_call(name: str, arguments: str, call_id: str = "call_1") -> dict:
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {"id": call_id, "type": "function", "function": {"name": name, "arguments": arguments}}
        ],
        "_model": "mock/model",
    }


def test_agent_runs_tool_then_answers(monkeypatch):
    calls = {"n": 0}

    def fake_chat(messages, tools=None, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return _tool_call("search_products", '{"age": 4, "gender": "girl", "occasion": "party"}')
        return _final("Here are some twirly party dresses for her!")

    monkeypatch.setattr(router, "chat", fake_chat)
    result = router.run_agent("router-test-1", "birthday outfit for my 4yo girl")

    assert "search_products" in result.tools_used
    assert result.products, "product cards should be extracted from tool output"
    assert "party dresses" in result.reply


def test_agent_handoff_flag(monkeypatch):
    calls = {"n": 0}

    def fake_chat(messages, tools=None, **kwargs):
        calls["n"] += 1
        if calls["n"] == 1:
            return _tool_call("escalate_to_human", '{"reason": "customer asked"}')
        return _final("Connecting you with a human agent now.")

    monkeypatch.setattr(router, "chat", fake_chat)
    result = router.run_agent("router-test-2", "I want to talk to a person")

    assert result.handoff is True
    assert "escalate_to_human" in result.tools_used


def test_agent_plain_reply(monkeypatch):
    def fake_chat(messages, tools=None, **kwargs):
        return _final("Hi! How can I help you today?")

    monkeypatch.setattr(router, "chat", fake_chat)
    result = router.run_agent("router-test-3", "hello")
    assert result.tools_used == []
    assert result.reply.startswith("Hi!")
