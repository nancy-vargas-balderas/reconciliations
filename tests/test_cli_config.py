import json
import tempfile
import unittest
from pathlib import Path

import click

from cli import _load_config


class CliConfigTest(unittest.TestCase):

    def test_loads_categories_and_recurring(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "categories": ["Housing", "Food"],
                        "recurring_expectations": {"rent": 1500, "gym": 75.5},
                    }
                ),
                encoding="utf-8",
            )

            categories, recurring = _load_config(config_path)
            self.assertEqual(categories, ["Housing", "Food"])
            self.assertEqual(recurring["rent"], 1500.0)
            self.assertEqual(recurring["gym"], 75.5)

    def test_invalid_categories_raises(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as tmp:
            tmp.write(json.dumps({"categories": "not-a-list"}))
            tmp.flush()
        try:
            with self.assertRaises(click.BadParameter):
                _load_config(Path(tmp.name))
        finally:
            Path(tmp.name).unlink(missing_ok=True)

    def test_invalid_recurring_amount(self) -> None:
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as tmp:
            tmp.write(json.dumps({"recurring_expectations": {"rent": "expensive"}}))
            tmp.flush()
        try:
            with self.assertRaises(click.BadParameter):
                _load_config(Path(tmp.name))
        finally:
            Path(tmp.name).unlink(missing_ok=True)
