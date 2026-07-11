import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from hymn_studio.timeline import Timeline


class TimelineTest(unittest.TestCase):
    def test_stores_transitions_in_order(self) -> None:
        timeline = Timeline()

        self.assertTrue(timeline.add_transition(1.0))
        self.assertTrue(timeline.add_transition(2.5))

        self.assertEqual(timeline.timestamps, [1.0, 2.5])

    def test_rejects_duplicate_or_backward_transitions(self) -> None:
        timeline = Timeline([1.0])

        self.assertFalse(timeline.add_transition(0.5))
        self.assertFalse(timeline.add_transition(1.01))
        self.assertEqual(timeline.timestamps, [1.0])

    def test_resolves_current_slide_index(self) -> None:
        timeline = Timeline([1.0, 3.0, 5.0])

        self.assertEqual(timeline.current_slide_index(0.5), 0)
        self.assertEqual(timeline.current_slide_index(1.0), 1)
        self.assertEqual(timeline.current_slide_index(4.0), 2)
        self.assertEqual(timeline.current_slide_index(6.0), 3)


if __name__ == "__main__":
    unittest.main()
