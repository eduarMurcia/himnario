import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from hymn_studio.services.audio_matcher import AudioMatcher, normalize_title


class NormalizeTitleTest(unittest.TestCase):
    def test_strips_accents_case_and_punctuation(self) -> None:
        self.assertEqual(
            normalize_title("¡Dad Loor al Señor!"), normalize_title("dad loor al senor")
        )


class AudioMatcherTest(unittest.TestCase):
    def test_matches_case_and_accent_insensitively(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "A la victoria Jesus nos llama.mp3").write_bytes(b"x")

            matcher = AudioMatcher(temp_path)
            match = matcher.find("A la Victoria Jesús Nos Llama")

            self.assertIsNotNone(match)
            self.assertEqual(match.name, "A la victoria Jesus nos llama.mp3")

    def test_returns_none_when_no_match(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            matcher = AudioMatcher(Path(temp_dir))
            self.assertIsNone(matcher.find("Unknown Hymn"))

    def test_prefers_variant_without_numeric_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "Anhelo Trabajar por el Senor.mp3").write_bytes(b"x")
            (temp_path / "Anhelo Trabajar por el Senor (2).mp3").write_bytes(b"x")

            matcher = AudioMatcher(temp_path)
            match = matcher.find("Anhelo Trabajar por el Senor")

            self.assertEqual(match.name, "Anhelo Trabajar por el Senor.mp3")

    def test_ignores_non_matching_extensions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "Cover Art.jpg").write_bytes(b"x")

            matcher = AudioMatcher(temp_path)
            self.assertIsNone(matcher.find("Cover Art"))

    def test_strips_leading_track_number(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            (temp_path / "043. Nuestra Fortaleza.mp3").write_bytes(b"x")
            (temp_path / "02 El placer de mi alma.mp3").write_bytes(b"x")

            matcher = AudioMatcher(temp_path)

            self.assertEqual(matcher.find("Nuestra Fortaleza").name, "043. Nuestra Fortaleza.mp3")
            self.assertEqual(
                matcher.find("El placer de mi alma").name, "02 El placer de mi alma.mp3"
            )

    def test_searches_multiple_directories(self) -> None:
        with tempfile.TemporaryDirectory() as dir_a, tempfile.TemporaryDirectory() as dir_b:
            path_a = Path(dir_a)
            path_b = Path(dir_b)
            (path_a / "Hymn One.mp3").write_bytes(b"x")
            (path_b / "Hymn Two.mp3").write_bytes(b"x")

            matcher = AudioMatcher([path_a, path_b])

            self.assertIsNotNone(matcher.find("Hymn One"))
            self.assertIsNotNone(matcher.find("Hymn Two"))


if __name__ == "__main__":
    unittest.main()
