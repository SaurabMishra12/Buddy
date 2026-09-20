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

    def test_corrupt_json_falls_back_to_defaults(self):
        """Config with invalid JSON should fall back to defaults and backup the corrupt file."""
        self.config_path.write_text("{broken json!!!", encoding="utf-8")
        cfg = Config(config_file=self.config_path)
        self.assertEqual(cfg.get("skin"), "thor")  # Default
        self.assertEqual(cfg.get("fps"), 60)  # Default
        # Corrupt file should be backed up
        backup = self.config_path.with_suffix(".json.bak")
        self.assertTrue(backup.exists())

    def test_non_dict_json_falls_back_to_defaults(self):
        """Config file containing a JSON array instead of dict should fall back to defaults."""
        self.config_path.write_text('[1, 2, 3]', encoding="utf-8")
        cfg = Config(config_file=self.config_path)
        self.assertEqual(cfg.get("skin"), "thor")

    def test_empty_config_file_uses_defaults(self):
        """Empty config file should use defaults without error."""
        self.config_path.write_text("", encoding="utf-8")
        cfg = Config(config_file=self.config_path)
        self.assertEqual(cfg.get("skin"), "thor")
        self.assertEqual(cfg.get("fps"), 60)

    def test_missing_config_file_uses_defaults(self):
        """Non-existent config file should use defaults."""
        missing = Path(self.temp_dir.name) / "nonexistent" / "config.json"
        cfg = Config(config_file=missing)
        self.assertEqual(cfg.get("skin"), "thor")

    def test_partial_config_merges_with_defaults(self):
        """Config file with only some keys should merge with defaults."""
        self.config_path.write_text('{"skin": "dragon", "fps": 30}', encoding="utf-8")
        cfg = Config(config_file=self.config_path)
        self.assertEqual(cfg.get("skin"), "dragon")
        self.assertEqual(cfg.get("fps"), 30)
        # Defaults should still be present
        self.assertEqual(cfg.get("scale"), 1.0)
        self.assertTrue(cfg.get("sound_enabled"))

    def test_reset_to_defaults(self):
        """reset_to_defaults should restore all settings."""
        self.config.set("skin", "dragon")
        self.config.set("fps", 30)
        self.config.reset_to_defaults()
        self.assertEqual(self.config.get("skin"), "thor")
        self.assertEqual(self.config.get("fps"), 60)


if __name__ == "__main__":
    unittest.main()
