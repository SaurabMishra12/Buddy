import unittest
import tempfile
import json
from pathlib import Path
from core.config import Config, DEFAULT_CONFIG


class TestConfig(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.config_path = Path(self.temp_dir.name) / "config.json"
        self.config = Config(config_file=self.config_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_default_values(self):
        self.assertEqual(self.config.get("skin"), "thor")
        self.assertEqual(self.config.get("fps"), 60)
        self.assertEqual(self.config.get("scale"), 1.0)
        self.assertFalse(self.config.get("click_through"))

    def test_set_and_save(self):
        self.config.set("skin", "dragon")
        self.assertEqual(self.config.get("skin"), "dragon")
        self.assertTrue(self.config_path.exists())

        # Verify disk contents
        with open(self.config_path, "r") as f:
            data = json.load(f)
        self.assertEqual(data["skin"], "dragon")

    def test_reload_from_disk(self):
        self.config.set("speed", 1.5)
        new_config = Config(config_file=self.config_path)
        self.assertEqual(new_config.get("speed"), 1.5)


if __name__ == "__main__":
    unittest.main()
