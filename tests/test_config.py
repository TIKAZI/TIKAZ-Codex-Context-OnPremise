import tempfile
import unittest
from pathlib import Path

from token_forge.config import load_config


class ConfigTests(unittest.TestCase):
    def test_loads_explicit_local_adapter_paths(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "local.toml"
            path.write_text(
                "[adapters]\nffmpeg = 'F:\\ffmpeg.exe'\nwhisper_model = 'G:\\model'\n"
                "[runtime]\ngpu_serial = true\nallow_remote = false\n",
                encoding="utf-8",
            )
            config = load_config(path)
            self.assertEqual(config.adapters["ffmpeg"], "F:\\ffmpeg.exe")
            self.assertTrue(config.gpu_serial)
            self.assertFalse(config.allow_remote)

    def test_missing_config_uses_safe_defaults(self):
        config = load_config(Path("definitely-missing-token-forge.toml"))
        self.assertEqual(config.adapters, {})
        self.assertTrue(config.gpu_serial)
        self.assertFalse(config.allow_remote)


if __name__ == "__main__":
    unittest.main()
