import sys
import types
import unittest


def _install_fake_sdk():
    """Stub the Gemini SDK so importing the client makes no network calls."""
    if "google.genai" in sys.modules:
        return
    google = types.ModuleType("google")
    genai = types.ModuleType("google.genai")
    genai_types = types.ModuleType("google.genai.types")

    class FakeClient:
        def __init__(self, api_key=None):
            self.api_key = api_key
            self.models = types.SimpleNamespace(generate_content=lambda **kw: None)

    class FakeConfig:
        def __init__(self, **kw):
            pass

    genai.Client = FakeClient
    genai_types.GenerateContentConfig = FakeConfig
    google.genai = genai
    sys.modules["google"] = google
    sys.modules["google.genai"] = genai
    sys.modules["google.genai.types"] = genai_types


_install_fake_sdk()

from src.gemini_client import (  # noqa: E402
    GeminiClientManager,
    is_daily_quota_error,
    is_dead_key_error,
    is_rate_limit_error,
    parse_retry_delay,
)


class FakeClock:
    """Controllable time so cooldown tests run instantly."""

    def __init__(self):
        self.now = 1000.0
        self.slept = []

    def monotonic(self):
        return self.now

    def sleep(self, seconds):
        self.slept.append(seconds)
        self.now += seconds


def manager(n_keys=3):
    clock = FakeClock()
    mgr = GeminiClientManager(
        keys=[f"key-{i}" for i in range(n_keys)],
        sleep=clock.sleep,
        monotonic=clock.monotonic,
    )
    return mgr, clock


class TestErrorClassification(unittest.TestCase):
    def test_rate_limit_markers(self):
        for err in ["429 RESOURCE_EXHAUSTED", "quota_exceeded", "Rate limit hit"]:
            self.assertTrue(is_rate_limit_error(err), err)
        self.assertFalse(is_rate_limit_error("500 internal error"))

    def test_daily_quota_is_distinguished_from_per_minute(self):
        daily = "429 RESOURCE_EXHAUSTED: GenerateRequestsPerDayPerProject exceeded"
        per_min = "429 RESOURCE_EXHAUSTED: GenerateRequestsPerMinute exceeded"
        self.assertTrue(is_daily_quota_error(daily))
        self.assertFalse(is_daily_quota_error(per_min))

    def test_dead_key_detected(self):
        self.assertTrue(is_dead_key_error("400 API_KEY_INVALID"))
        self.assertFalse(is_dead_key_error("429 RESOURCE_EXHAUSTED"))

    def test_retry_delay_parsed_from_error_body(self):
        self.assertEqual(parse_retry_delay("... 'retryDelay': '27s' ..."), 27.0)
        self.assertEqual(parse_retry_delay('"retryDelay": "5s"'), 5.0)
        self.assertIsNone(parse_retry_delay("429 RESOURCE_EXHAUSTED"))


class TestRotation(unittest.TestCase):
    def test_startup_makes_no_api_calls(self):
        # The old implementation sent one live generate_content per key on import.
        calls = []
        import src.gemini_client as gc

        original = gc.genai.Client

        # Replace rather than subclass: the real SDK client exposes `models` as a
        # read-only property, so a subclass cannot install a counting stub.
        class CountingClient:
            def __init__(self, api_key=None):
                calls.append(api_key)
                self.models = types.SimpleNamespace(
                    generate_content=lambda **kw: calls.append("REQUEST")
                )

        gc.genai.Client = CountingClient
        try:
            GeminiClientManager(keys=["a", "b", "c"])
        finally:
            gc.genai.Client = original

        self.assertNotIn("REQUEST", calls, "startup must not spend API requests")

    def test_rotates_forward_through_keys(self):
        mgr, _ = manager(3)
        self.assertEqual(mgr.current_index, 0)
        mgr.mark_failed("429 RESOURCE_EXHAUSTED")
        mgr.rotate_key()
        self.assertEqual(mgr.current_index, 1)

    def test_wraps_around_after_waiting_instead_of_aborting(self):
        # The original bug: three throttled keys ended the entire run, even
        # though key 1 was usable again a minute later.
        mgr, clock = manager(3)
        for _ in range(3):
            mgr.mark_failed("429 RESOURCE_EXHAUSTED: quota")
            mgr.rotate_key()

        self.assertTrue(clock.slept, "expected a cooldown wait rather than an abort")
        self.assertEqual(mgr.current_index, 0, "should come back around to key 1")

    def test_honours_retry_delay_from_the_error(self):
        mgr, clock = manager(1)
        mgr.mark_failed("429 RESOURCE_EXHAUSTED {'retryDelay': '12s'}")
        mgr.rotate_key()
        self.assertEqual(clock.slept, [12.0])

    def test_daily_quota_retires_key_without_waiting(self):
        mgr, clock = manager(2)
        mgr.mark_failed("429 GenerateRequestsPerDay exceeded")
        mgr.rotate_key()
        self.assertIn(0, mgr.retired)
        self.assertEqual(mgr.current_index, 1)
        self.assertEqual(clock.slept, [], "daily quota should not be waited out")

    def test_all_keys_daily_exhausted_raises(self):
        mgr, _ = manager(2)
        with self.assertRaises(RuntimeError):
            for _ in range(2):
                mgr.mark_failed("429 GenerateRequestsPerDay exceeded")
                mgr.rotate_key()

    def test_invalid_key_is_retired_not_cooled(self):
        mgr, clock = manager(2)
        mgr.mark_failed("400 API_KEY_INVALID")
        mgr.rotate_key()
        self.assertIn(0, mgr.retired)
        self.assertEqual(clock.slept, [])

    def test_total_wait_is_capped(self):
        mgr, _ = manager(1)
        import src.gemini_client as gc

        mgr.total_waited = gc.MAX_TOTAL_WAIT_SECONDS
        mgr.mark_failed("429 RESOURCE_EXHAUSTED")
        with self.assertRaises(RuntimeError):
            mgr.rotate_key()


if __name__ == "__main__":
    unittest.main()
