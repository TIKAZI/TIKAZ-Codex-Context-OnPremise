import json
import tempfile
import unittest
from pathlib import Path

from token_forge.model_profiles import describe_model, load_model_profiles


class ModelProfileTests(unittest.TestCase):
    def test_registry_is_valid_and_known_profile_is_not_runtime_proof(self):
        data = load_model_profiles()
        self.assertEqual(data["schema_version"], "model-profiles/v1")
        profile = describe_model("qwen3-vl:8b")
        self.assertEqual(profile["status"], "tested-default")
        self.assertFalse(profile["verified"])
        self.assertTrue(profile["historically_fixture_validated"])
        self.assertEqual(profile["actual_model"], "UNVERIFIED")

    def test_unknown_model_stays_unverified(self):
        profile = describe_model("future-local-vlm:1b")
        self.assertEqual(profile["status"], "unknown-unverified")
        self.assertFalse(profile["verified"])

    def test_invalid_registry_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "profiles.json"
            path.write_text(json.dumps({"schema_version": "old", "profiles": []}), encoding="utf-8")
            with self.assertRaises(ValueError):
                load_model_profiles(path)


