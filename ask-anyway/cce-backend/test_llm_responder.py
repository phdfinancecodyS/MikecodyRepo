"""Responder unit tests for provider failover and token budget protection."""
import importlib
import os
import time
import unittest


class _Msg:
    def __init__(self, text):
        self.content = text


class _Choice:
    def __init__(self, text):
        self.message = _Msg(text)


class _Usage:
    def __init__(self, prompt_tokens=0, completion_tokens=0):
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens


class _Resp:
    def __init__(self, text, prompt_tokens=0, completion_tokens=0):
        self.choices = [_Choice(text)]
        self.usage = _Usage(prompt_tokens, completion_tokens)


class _ChatCompletions:
    def __init__(self, fn):
        self._fn = fn

    def create(self, **kwargs):
        return self._fn(**kwargs)


class _Chat:
    def __init__(self, fn):
        self.completions = _ChatCompletions(fn)


class _Client:
    def __init__(self, fn):
        self.chat = _Chat(fn)


class LlmResponderTests(unittest.TestCase):
    def setUp(self):
        os.environ["CCE_LLM_PROVIDER_CHAIN"] = "groq,openai"
        os.environ["CCE_LLM_ENABLED_STEPS"] = "deepening"
        self.mod = importlib.import_module("src.llm_responder")
        self.mod = importlib.reload(self.mod)

    def test_rate_limit_falls_back_to_next_provider(self):
        def groq_fail(**kwargs):
            raise Exception("429 rate limit")

        def openai_ok(**kwargs):
            return _Resp("fallback ok", prompt_tokens=10, completion_tokens=6)

        clients = {
            "groq": _Client(groq_fail),
            "openai": _Client(openai_ok),
        }

        self.mod._PROVIDER_CHAIN = ["groq", "openai"]
        self.mod._PROVIDER_COOLDOWN = {"groq": 0.0, "openai": 0.0}
        self.mod._RESPONSE_CACHE = {}
        self.mod._TOKEN_EVENTS = []
        self.mod._BUDGET_BLOCK_UNTIL = 0.0
        self.mod._get_client = lambda provider: clients.get(provider)
        self.mod._model_for = lambda provider: "fake-model"

        out = self.mod._call_llm("system", "user")

        self.assertEqual(out, "fallback ok")
        self.assertGreater(self.mod._PROVIDER_COOLDOWN["groq"], time.time() - 1)

    def test_budget_block_prevents_provider_call(self):
        self.mod._BUDGET_TOKENS_PER_MINUTE = 10
        self.mod._BUDGET_TOKENS_PER_HOUR = 0
        self.mod._BUDGET_TOKENS_PER_DAY = 0
        self.mod._PROVIDER_CHAIN = ["openai"]
        self.mod._PROVIDER_COOLDOWN = {"openai": 0.0}
        now = time.time()
        self.mod._TOKEN_EVENTS = [(now - 5, 10)]
        self.mod._BUDGET_BLOCK_UNTIL = 0.0

        called = {"count": 0}

        def should_not_call(provider):
            called["count"] += 1
            return None

        self.mod._get_client = should_not_call
        self.mod._RESPONSE_CACHE = {}

        out = self.mod._call_llm("system", "user")

        self.assertIsNone(out)
        self.assertEqual(called["count"], 0)
        self.assertGreater(self.mod._BUDGET_BLOCK_UNTIL, now)


if __name__ == "__main__":
    unittest.main()
