import tempfile
import unittest
from pathlib import Path

from token_forge.adapters import AdapterSpec, probe_adapter


class AdapterTests(unittest.TestCase):
    def test_probe_accepts_an_explicit_existing_executable(self):
        with tempfile.TemporaryDirectory() as temp:
            executable = Path(temp) / "adapter.exe"
            executable.write_bytes(b"")
            status = probe_adapter(AdapterSpec("fixture", (str(executable),)))
            self.assertTrue(status.available)
            self.assertEqual(Path(status.executable), executable)

    def test_probe_reports_missing_adapter_without_installing(self):
        status = probe_adapter(AdapterSpec("missing", ("definitely-not-installed-token-forge",)))
        self.assertFalse(status.available)
        self.assertIsNone(status.executable)


if __name__ == "__main__":
    unittest.main()

