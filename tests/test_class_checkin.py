import re
import unittest

from src.pipelines.class_checkin import (
    checkin_decision,
    checkin_risk_flags,
    generate_class_access_code,
)


class ClassCheckinTests(unittest.TestCase):
    def test_generates_eight_digit_codes_with_leading_zeroes_preserved(self):
        for _ in range(100):
            self.assertRegex(generate_class_access_code(), re.compile(r"^\d{8}$"))

    def test_auto_approves_high_confidence_face_match(self):
        self.assertEqual(checkin_decision("face", 0.3), ("approved", ()))

    def test_sends_borderline_face_match_to_teacher_review(self):
        self.assertEqual(
            checkin_decision("face", 0.5),
            ("pending", ("borderline_face_match",)),
        )

    def test_auto_approves_high_confidence_voice_match(self):
        self.assertEqual(checkin_decision("voice", 0.9), ("approved", ()))

    def test_sends_borderline_voice_match_to_teacher_review(self):
        self.assertEqual(
            checkin_decision("voice", 0.7),
            ("pending", ("borderline_voice_match",)),
        )

    def test_rejects_unmatched_scores_and_unknown_methods(self):
        with self.assertRaises(ValueError):
            checkin_decision("face", 0.61)
        with self.assertRaises(ValueError):
            checkin_decision("voice", 0.64)
        with self.assertRaises(ValueError):
            checkin_decision("manual", 0.9)

    def test_flags_inaccurate_optional_location(self):
        self.assertEqual(
            checkin_risk_flags("face", 0.5, location_accuracy_m=250),
            ("borderline_face_match", "low_gps_accuracy"),
        )
        self.assertEqual(checkin_risk_flags("face", 0.3), ())


if __name__ == "__main__":
    unittest.main()
