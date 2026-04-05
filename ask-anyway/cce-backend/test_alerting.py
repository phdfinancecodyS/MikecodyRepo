"""Unit tests for SMS alert delivery helper."""
import importlib
import os
import tempfile
import unittest


class _Resp:
    def __init__(self):
        self._payload = {"sid": "SM123", "status": "queued"}

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class AlertingTests(unittest.TestCase):
    def setUp(self):
        os.environ["CCE_ALERT_SMS_ENABLED"] = "1"
        os.environ["TWILIO_ACCOUNT_SID"] = "AC-test"
        os.environ["TWILIO_AUTH_TOKEN"] = "token-test"
        os.environ["TWILIO_FROM_NUMBER"] = "+15550000001"
        os.environ["CCE_ALERT_SMS_TO"] = "+15550000002"
        os.environ["CCE_ALERT_SMS_DEDUP_SECONDS"] = "3600"

        self.mod = importlib.import_module("src.alerting")
        self.mod = importlib.reload(self.mod)

    def test_autosend_interval_default_is_48h(self):
        os.environ.pop("CCE_ALERT_SMS_INTERVAL_HOURS", None)
        self.mod = importlib.reload(self.mod)
        self.assertEqual(self.mod._autosend_interval_seconds(), 48 * 3600)

    def test_seconds_until_next_run_uses_state_file(self):
        with tempfile.TemporaryDirectory() as td:
            state_file = os.path.join(td, "alert_state.json")
            os.environ["CCE_ALERT_SMS_STATE_FILE"] = state_file
            self.mod = importlib.reload(self.mod)

            self.assertEqual(self.mod._seconds_until_next_run(1000.0, 3600), 0.0)

            self.mod._write_last_auto_run_ts(1000.0)
            self.assertEqual(self.mod._seconds_until_next_run(1200.0, 3600), 3400.0)

    def test_send_sms_with_alerts(self):
        self.mod.metrics.llm_alerts_snapshot = lambda min_level="warning": {
            "has_alerts": True,
            "alerts": [
                {
                    "window": "hour",
                    "level": "warning",
                    "used_pct": 84.0,
                    "recommended_action": "switch to peak",
                }
            ],
        }

        calls = {"count": 0}

        def fake_post(*args, **kwargs):
            calls["count"] += 1
            return _Resp()

        self.mod.requests.post = fake_post

        out = self.mod.send_llm_alerts_sms(min_level="warning")

        self.assertTrue(out["ok"])
        self.assertTrue(out["sent"])
        self.assertEqual(calls["count"], 1)

    def test_dedup_skips_duplicate_body(self):
        self.mod.metrics.llm_alerts_snapshot = lambda min_level="warning": {
            "has_alerts": True,
            "alerts": [
                {
                    "window": "minute",
                    "level": "critical",
                    "used_pct": 99.0,
                    "recommended_action": "disable llm",
                }
            ],
        }

        calls = {"count": 0}

        def fake_post(*args, **kwargs):
            calls["count"] += 1
            return _Resp()

        self.mod.requests.post = fake_post

        first = self.mod.send_llm_alerts_sms(min_level="warning")
        second = self.mod.send_llm_alerts_sms(min_level="warning")

        self.assertTrue(first["sent"])
        self.assertFalse(second["sent"])
        self.assertEqual(second["reason"], "deduped")
        self.assertEqual(calls["count"], 1)


if __name__ == "__main__":
    unittest.main()
