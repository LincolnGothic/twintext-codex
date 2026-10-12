import io
import json
import os
import tempfile
import threading
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.error import HTTPError, URLError

from test_core import FakeEngine

from twintext.config import TwinTextError, load_settings, update_settings
from twintext.mcp import call_tool
from twintext.service import Service


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        environment = patch.dict(os.environ, {"TWINTEXT_HOME": self.directory.name})
        environment.start()
        self.addCleanup(environment.stop)

    def test_legacy_settings_default_offline_and_explicit_selection(self):
        Path(self.directory.name, "settings.json").write_text('{"target":"zh"}')
        self.assertEqual(load_settings().provider, "offline")
        update_settings(provider="azure")
        self.assertEqual(load_settings().provider, "azure")
        with self.assertRaises(TwinTextError):
            update_settings(provider="unknown")
        self.assertEqual(load_settings().provider, "azure")

    def test_service_refreshes_selection_and_preserves_injection(self):
        from twintext.providers import AzureEngine

        service = Service()
        self.assertEqual(service.engine.provider, "offline")
        update_settings(provider="azure")
        self.assertIsInstance(service.engine, AzureEngine)
        injected = FakeEngine()
        self.assertIs(Service(engine=injected).engine, injected)

    def test_cache_is_separated_even_when_engine_fingerprints_match(self):
        engine = FakeEngine()
        service = Service(engine)
        update_settings(source="en", target="zh")
        service.translate("Hello")
        update_settings(provider="azure")
        self.assertEqual(service.translate("Hello")["cache_hits"], 0)
        self.assertEqual(len(engine.calls), 2)
        update_settings(provider="offline")
        self.assertEqual(service.translate("Hello")["cache_hits"], 1)

    def test_language_mapping_and_identity(self):
        from twintext.providers import AzureEngine, azure_language

        for source, mapped in {
            "en": "en",
            "zh": "zh-Hans",
            "ja": "ja",
            "fr": "fr",
            "es": "es",
        }.items():
            self.assertEqual(azure_language(source), mapped)
        with self.assertRaisesRegex(TwinTextError, "language"):
            azure_language("xx")
        self.assertEqual(AzureEngine().translate("Hello", "en", "en"), "Hello")

    def engine(
        self, response=b'[{"translations":[{"text":"Bonjour","to":"fr"}]}]', error=None, cancel=None
    ):
        from twintext.providers import AzureEngine

        self.sent = []

        def send(request, timeout):
            self.sent.append((request, timeout))
            if error:
                raise error
            if cancel:
                cancel.set()
            return io.BytesIO(response)

        return AzureEngine(
            opener=send, credentials=lambda: {"key": "fixture-secret", "region": "westus"}
        )

    def test_request_response_and_metadata_only_usage(self):
        from twintext.usage import CloudUsage

        engine = self.engine()
        self.assertEqual(engine.translate("Hello😀", "zh", "fr"), "Bonjour")
        request, timeout = self.sent[0]
        self.assertIn("from=zh-Hans", request.full_url)
        self.assertIn("api-version=3.0", request.full_url)
        self.assertEqual(json.loads(request.data), [{"Text": "Hello😀"}])
        self.assertGreater(timeout, 0)
        self.assertNotIn("fixture-secret", engine.fingerprint("zh", "fr"))
        self.assertEqual(CloudUsage().snapshot()["requests"], 1)
        self.assertEqual(CloudUsage().snapshot()["characters"], 6)
        raw = Path(self.directory.name, "cloud-usage.json").read_text()
        for forbidden in ("Hello", "Bonjour", "fixture-secret"):
            self.assertNotIn(forbidden, raw)

    def test_http_and_network_errors_are_sanitized(self):
        for code, message in [
            (400, "language"),
            (401, "credentials"),
            (403, "quota"),
            (408, "timed out"),
            (429, "rate limit"),
            (500, "unavailable"),
            (302, "redirect"),
        ]:
            with self.subTest(code=code):
                engine = self.engine(
                    error=HTTPError(
                        "https://example", code, "fixture-secret", {}, io.BytesIO(b"fixture-secret")
                    )
                )
                with self.assertRaisesRegex(TwinTextError, message) as error:
                    engine.translate("Hello", "en", "fr")
                self.assertNotIn("fixture-secret", str(error.exception))
        for error, message in [
            (TimeoutError("fixture-secret"), "timed out"),
            (URLError("fixture-secret"), "network"),
        ]:
            with self.assertRaisesRegex(TwinTextError, message):
                self.engine(error=error).translate("Hello", "en", "fr")

    def test_missing_credentials_never_sends_or_counts(self):
        from twintext.providers import AzureEngine
        from twintext.usage import CloudUsage

        engine = AzureEngine(
            opener=lambda *a, **k: self.fail("network called"), credentials=lambda: {}
        )
        with self.assertRaisesRegex(TwinTextError, "Configure"):
            engine.translate("Hello", "en", "fr")
        self.assertEqual(CloudUsage().snapshot()["requests"], 0)

    def test_malformed_and_empty_responses(self):
        for body, message in [
            (b"not json", "invalid response"),
            (b"{}", "invalid response"),
            (b"[]", "empty translation"),
            (b'[{"translations":[]}]', "empty translation"),
            (b'[{"translations":[{"text":" "}]}]', "empty translation"),
            (b'[{"translations":[{"text":123}]}]', "invalid response"),
            (b'[{"translations":[{"text":"OK","to":"ja"}]}]', "invalid response"),
        ]:
            with self.subTest(body=body), self.assertRaisesRegex(TwinTextError, message):
                self.engine(response=body).translate("Hello", "en", "fr")

    def test_cancellation_before_and_after_request(self):
        cancelled = threading.Event()
        cancelled.set()
        engine = self.engine()
        with self.assertRaisesRegex(TwinTextError, "cancelled"):
            engine.translate("Hello", "en", "fr", cancel=cancelled)
        self.assertEqual(self.sent, [])
        cancelled.clear()
        with self.assertRaisesRegex(TwinTextError, "cancelled"):
            self.engine(cancel=cancelled).translate("Hello", "en", "fr", cancel=cancelled)

    def test_service_cancellation_does_not_cache_or_continue_fragments(self):
        cancelled = threading.Event()
        update_settings(source="en", target="fr", provider="azure")
        service = Service(self.engine(cancel=cancelled))
        with self.assertRaisesRegex(TwinTextError, "cancelled"):
            service.translate("First paragraph.\n\nSecond paragraph.", cancel=cancelled)
        self.assertEqual(len(self.sent), 1)
        cancelled.clear()
        service = Service(self.engine())
        self.assertEqual(service.translate("First paragraph.")["cache_hits"], 0)

    def test_wrapped_timeout_and_invalid_stored_headers_are_sanitized(self):
        with self.assertRaisesRegex(TwinTextError, "timed out"):
            self.engine(error=URLError(TimeoutError("fixture-secret"))).translate(
                "Hello", "en", "fr"
            )
        from twintext.credentials import save_credentials

        for key, region in [("fixture-secret\r\nInjected: bad", "westus"),
                            ("fixture-secret", "westus\r\nInjected: bad")]:
            with self.assertRaises(TwinTextError) as error:
                save_credentials(key, region)
            self.assertNotIn("fixture-secret", str(error.exception))

    def test_windows_credential_manager_backend_without_real_credentials(self):
        import ctypes

        from twintext.credentials import load_credentials, save_credentials

        api = Mock()
        stored = {}
        retained = []

        def write(pointer, flags):
            item = ctypes.cast(pointer, api.CredWriteW.argtypes[0]).contents
            stored["target"] = item.TargetName
            stored["blob"] = ctypes.string_at(item.CredentialBlob, item.CredentialBlobSize)
            self.assertEqual(item.Persist, 2)
            return True

        def read(target, kind, flags, output):
            pointer_type = api.CredReadW.argtypes[-1]._type_
            item_type = pointer_type._type_
            blob = (ctypes.c_ubyte * len(stored["blob"])).from_buffer_copy(stored["blob"])
            item = item_type(CredentialBlobSize=len(blob), CredentialBlob=blob)
            retained.extend([blob, item])
            ctypes.cast(output, ctypes.POINTER(pointer_type))[0] = ctypes.pointer(item)
            self.assertEqual(target, stored["target"])
            return True

        api.CredWriteW.side_effect = write
        api.CredReadW.side_effect = read
        with patch("twintext.credentials.sys.platform", "win32"), \
                patch("ctypes.WinDLL", return_value=api, create=True):
            save_credentials("fixture-secret", "westus")
            self.assertEqual(load_credentials(), {"key": "fixture-secret", "region": "westus"})
        self.assertFalse(Path(self.directory.name, "private").exists())
        self.assertNotIn("fixture-secret", stored["target"])
        api.CredFree.assert_called_once()

    def test_usage_rollover_persistence_and_cache_hits(self):
        from twintext.usage import CloudUsage

        usage = CloudUsage(today=lambda: date(2026, 10, 31))
        usage.record(123)
        usage.record(5)
        self.assertEqual(usage.snapshot()["characters"], 128)
        self.assertEqual(usage.snapshot()["requests"], 2)
        november = CloudUsage(today=lambda: date(2026, 11, 1))
        self.assertEqual(november.snapshot()["requests"], 0)
        november.record(7)
        self.assertEqual(november.snapshot()["characters"], 7)
        update_settings(source="en", target="fr", provider="azure")
        service = Service(self.engine())
        service.translate("Hello")
        before = CloudUsage().snapshot()["requests"]
        service.translate("Hello")
        self.assertEqual(CloudUsage().snapshot()["requests"], before)

    def test_keys_never_enter_settings_status_or_mcp(self):
        update_settings(provider="azure")
        with patch("twintext.providers.load_credentials", return_value={"key": "fixture-secret"}):
            result = Service().status()
        self.assertTrue(result["azure_configured"])
        self.assertEqual(result["provider"], "azure")
        self.assertNotIn("fixture-secret", json.dumps(result))
        self.assertNotIn("fixture-secret", Path(self.directory.name, "settings.json").read_text())
        with self.assertRaises(TwinTextError):
            call_tool("twintext_set_settings", {"azure_key": "fixture-secret"}, Service())

    def test_mcp_provider_setting_and_model_controls(self):
        result = call_tool("twintext_set_settings", {"provider": "azure"}, Service())
        self.assertEqual(result["provider"], "azure")
        with self.assertRaisesRegex(TwinTextError, "Offline"):
            call_tool("twintext_install_models", {}, Service())

    def test_web_credentials_are_status_only(self):
        from twintext.ui import html

        page = html(embedded=True)
        self.assertIn('id="provider"', page)
        self.assertIn('id="azure-status"', page)
        self.assertNotIn('type="password"', page)
        self.assertNotIn("Ocp-Apim-Subscription-Key", page)

    @unittest.skipIf(os.name == "nt", "Unix private file backend")
    def test_credentials_private_permissions_and_no_symlinks(self):
        from twintext.credentials import load_credentials, save_credentials

        save_credentials("fixture-secret", "westus")
        path = Path(self.directory.name, "private", "azure-credentials.json")
        self.assertEqual(path.stat().st_mode & 0o777, 0o600)
        self.assertEqual(path.parent.stat().st_mode & 0o777, 0o700)
        self.assertEqual(load_credentials()["key"], "fixture-secret")
        path.chmod(0o644)
        with self.assertRaisesRegex(TwinTextError, "permissions"):
            load_credentials()


if __name__ == "__main__":
    unittest.main()
