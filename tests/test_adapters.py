import tempfile
import unittest
from pathlib import Path

from token_forge.adapters import AdapterSpec, default_adapter_specs, probe_adapter


class AdapterTests(unittest.TestCase):
    def test_probe_accepts_an_explicit_existing_executable(self):
        with tempfile.TemporaryDirectory() as temp:
            executable = Path(temp) / "adapter.exe"
            executable.write_bytes(b"")
            status = probe_adapter(AdapterSpec("fixture", (str(executable),)))
            self.assertTrue(status.available)
            self.assertTrue(Path(status.executable).samefile(executable))

    def test_probe_reports_missing_adapter_without_installing(self):
        status = probe_adapter(AdapterSpec("missing", ("definitely-not-installed-token-forge",)))
        self.assertFalse(status.available)
        self.assertIsNone(status.executable)

    def test_all_optional_adapters_accept_explicit_isolated_paths(self):
        configured = {
            "node": "G:/node/node.exe",
            "markitdown": "G:/envs/documents/markitdown.exe",
            "docling": "G:/envs/documents/docling.exe",
            "mineru": "G:/envs/mineru/mineru.exe",
            "paddleocr": "G:/envs/paddleocr/paddleocr.exe",
            "paddleocr_python": "G:/envs/paddleocr/python.exe",
            "ollama": "G:/runtimes/ollama/ollama.exe",
            "defuddle": "G:/node/defuddle.CMD",
            "playwright": "G:/node/playwright.CMD",
            "yt_dlp": "G:/envs/media/yt-dlp.exe",
            "scenedetect": "G:/envs/media/scenedetect.exe",
            "retrieval_python": "G:/envs/retrieval/python.exe",
            "llmlingua_python": "G:/envs/llmlingua/python.exe",
        }
        specs = {spec.name: spec for spec in default_adapter_specs(configured)}
        for key, path in configured.items():
            expected_name = key.replace("_", "-")
            self.assertEqual(specs[expected_name].candidates[0], path)


if __name__ == "__main__":
    unittest.main()
