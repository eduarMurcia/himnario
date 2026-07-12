import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hymn_studio.services.template_config import PillowTemplateConfig, TemplateConfigError


class PillowTemplateConfigTest(unittest.TestCase):
    def test_builds_templates_with_relative_paths_and_overlays(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "font.ttf").write_bytes(b"fake-font")
            (temp_path / "ornament.png").write_bytes(b"fake-ornament")

            config_data = {
                "cover": {
                    "font": "font.ttf",
                    "font_size": 133,
                    "text_color": [246, 235, 213],
                    "text_box": [553, 296, 1155, 173],
                    "align": "left",
                    "wrap": False,
                    "extra_overlays": [
                        {
                            "text": "Subtitle",
                            "font": "font.ttf",
                            "font_size": 56,
                            "text_box": [553, 595, 924, 82],
                            "align": "left",
                            "wrap": False,
                        }
                    ],
                    "image_overlays": [{"image": "ornament.png", "box": [553, 471, 763, 40]}],
                },
                "stanza": {
                    "font": "font.ttf",
                    "font_size": 150,
                    "text_box": [275, 143, 1412, 789],
                    "line_spacing": 1.15,
                },
            }
            config_path = temp_path / "template.json"
            config_path.write_text(json.dumps(config_data), encoding="utf-8")

            config = PillowTemplateConfig(config_path)
            cover = config.build_cover_template(Path("portada.png"))
            stanza = config.build_stanza_template(Path("cuerpo.png"))

            self.assertEqual(cover.background, Path("portada.png"))
            self.assertEqual(cover.font_path, temp_path / "font.ttf")
            self.assertEqual(cover.font_size, 133)
            self.assertFalse(cover.wrap)
            self.assertEqual(len(cover.extra_overlays), 1)
            self.assertEqual(cover.extra_overlays[0].text, "Subtitle")
            self.assertEqual(len(cover.image_overlays), 1)
            self.assertEqual(cover.image_overlays[0].image, temp_path / "ornament.png")

            self.assertEqual(stanza.background, Path("cuerpo.png"))
            self.assertEqual(stanza.line_spacing, 1.15)

    def test_raises_on_missing_section(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "template.json"
            config_path.write_text(json.dumps({"cover": {"font": "f.ttf", "font_size": 10}}))

            config = PillowTemplateConfig(config_path)
            with self.assertRaises(TemplateConfigError):
                config.build_stanza_template(Path("bg.png"))

    def test_raises_on_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "template.json"
            config_path.write_text("not json")

            with self.assertRaises(TemplateConfigError):
                PillowTemplateConfig(config_path)


if __name__ == "__main__":
    unittest.main()
