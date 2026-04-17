import json
import tempfile
import unittest
from pathlib import Path

from app.services.format_registry import DuplicateFormatError, FormatRegistry


class TestFormatRegistry(unittest.TestCase):
    def _fields(self):
        return [
            {
                "tag": "依頼日",
                "box": {"x": 100, "y": 100, "w": 200, "h": 60},
                "source_image_width": 2000,
                "source_image_height": 1000,
            },
            {
                "tag": "担当者",
                "box": {"x": 500, "y": 100, "w": 200, "h": 60},
                "source_image_width": 2000,
                "source_image_height": 1000,
            },
        ]

    def test_duplicate_detection_with_similar_layout(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "formats.json"
            path.write_text(json.dumps({"formats": []}), encoding="utf-8")
            registry = FormatRegistry(path)

            registry.add_format("fmt1", (842, 595), self._fields())

            similar = [
                {
                    "tag": "依頼日",
                    "box": {"x": 102, "y": 102, "w": 198, "h": 59},
                    "source_image_width": 2000,
                    "source_image_height": 1000,
                },
                {
                    "tag": "担当者",
                    "box": {"x": 502, "y": 101, "w": 201, "h": 61},
                    "source_image_width": 2000,
                    "source_image_height": 1000,
                },
            ]

            with self.assertRaises(DuplicateFormatError):
                registry.add_format("fmt1_copy", (842, 595), similar)

    def test_rename_and_delete(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "formats.json"
            path.write_text(json.dumps({"formats": []}), encoding="utf-8")
            registry = FormatRegistry(path)

            created = registry.add_format("fmt1", (842, 595), self._fields())
            fmt_id = created["format_id"]

            renamed = registry.rename_format(fmt_id, "fmt1_new")
            self.assertTrue(renamed)
            fetched = registry.get_format(fmt_id)
            self.assertIsNotNone(fetched)
            self.assertEqual(fetched["name"], "fmt1_new")

            deleted = registry.delete_format(fmt_id)
            self.assertTrue(deleted)
            self.assertIsNone(registry.get_format(fmt_id))


if __name__ == "__main__":
    unittest.main()
