import unittest

from src.screens.student_screen import (
    _get_pose_camera_config,
    check_pose_orientation,
    get_pose_capture_feedback,
)


class PoseOrientationGuidanceTests(unittest.TestCase):
    def test_camera_config_for_all_poses(self):
        poses = ["front", "left", "right", "left_profile", "right_profile"]
        for pose in poses:
            cfg = _get_pose_camera_config(pose)
            self.assertIn("hud_title", cfg)
            self.assertIn("hud_subtitle", cfg)
            self.assertIn("camera_label", cfg)
            self.assertIn("framing_tip", cfg)
            self.assertIn("gradient", cfg)
            self.assertIn("border_color", cfg)

    def test_camera_config_slight_left_direction(self):
        cfg = _get_pose_camera_config("left")
        self.assertIn("LEFT", cfg["hud_title"])
        self.assertIn("⟵", cfg["hud_title"])
        self.assertIn("LEFT", cfg["camera_label"])

    def test_check_pose_orientation_front(self):
        self.assertTrue(check_pose_orientation("front", 0.0))
        self.assertTrue(check_pose_orientation("front", 15.0))
        self.assertTrue(check_pose_orientation("front", -15.0))
        self.assertFalse(check_pose_orientation("front", 25.0))
        self.assertFalse(check_pose_orientation("front", -25.0))

    def test_check_pose_orientation_slight_left(self):
        # Valid left range: -30° to -65° (exclusive)
        self.assertTrue(check_pose_orientation("left", -35.0))
        self.assertTrue(check_pose_orientation("left", -50.0))
        self.assertTrue(check_pose_orientation("left", -64.9))
        self.assertFalse(check_pose_orientation("left", -5.0))    # too centered
        self.assertFalse(check_pose_orientation("left", -66.0))   # too far → profile
        self.assertFalse(check_pose_orientation("left", 35.0))    # wrong direction

    def test_check_pose_orientation_slight_right(self):
        # Valid right range: 30° to 65° (exclusive)
        self.assertTrue(check_pose_orientation("right", 35.0))
        self.assertTrue(check_pose_orientation("right", 50.0))
        self.assertTrue(check_pose_orientation("right", 64.9))
        self.assertFalse(check_pose_orientation("right", 5.0))    # too centered
        self.assertFalse(check_pose_orientation("right", 66.0))   # too far → profile
        self.assertFalse(check_pose_orientation("right", -35.0))  # wrong direction

    def test_check_pose_orientation_profiles(self):
        # Full profile threshold is now 65°
        self.assertTrue(check_pose_orientation("left_profile", -66.0))
        self.assertTrue(check_pose_orientation("left_profile", -80.0))
        self.assertFalse(check_pose_orientation("left_profile", -60.0))  # not deep enough
        self.assertFalse(check_pose_orientation("left_profile", -30.0))
        self.assertTrue(check_pose_orientation("right_profile", 66.0))
        self.assertTrue(check_pose_orientation("right_profile", 80.0))
        self.assertFalse(check_pose_orientation("right_profile", 60.0))
        self.assertFalse(check_pose_orientation("right_profile", 30.0))

    def test_profile_accepts_detected_profile_label_when_yaw_is_uncertain(self):
        self.assertTrue(
            check_pose_orientation(
                "left_profile",
                7.0,
                detected_pose_label="left_profile",
            )
        )
        self.assertTrue(
            check_pose_orientation(
                "right_profile",
                -7.0,
                detected_pose_label="right_profile",
            )
        )

    def test_slight_right_accepts_moderate_positive_yaw(self):
        self.assertTrue(check_pose_orientation("right", 13.4))
        self.assertTrue(check_pose_orientation("left", -13.4))

    def test_get_pose_capture_feedback_no_face(self):
        feedback = get_pose_capture_feedback("front", {"face_count": 0})
        self.assertIn("No face detected", feedback)

    def test_get_pose_capture_feedback_multiple_faces(self):
        feedback = get_pose_capture_feedback("front", {"face_count": 2})
        self.assertIn("2 faces detected", feedback)

    def test_get_pose_capture_feedback_invalid_quality(self):
        feedback = get_pose_capture_feedback(
            "front",
            {
                "face_count": 1,
                "valid": False,
                "brightness": 15.0,
                "sharpness": 1.0,
                "face_ratio": 0.005,
            },
        )
        self.assertIn("Image quality is too low", feedback)

    def test_get_pose_capture_feedback_left_too_centered(self):
        # Aiming for 'left' but still near-front (-5° is way too centered)
        feedback = get_pose_capture_feedback(
            "left",
            {
                "face_count": 1,
                "valid": True,
                "yaw_degrees": -5.0,
                "eye_width_ratio": 1.0,
                "brightness": 120.0,
                "sharpness": 5.0,
                "face_ratio": 0.05,
            },
        )
        self.assertIn("still too centered", feedback)

    def test_get_pose_capture_feedback_right_too_far(self):
        # Aiming for 'right' but pushed into full profile (82° > 65°)
        feedback = get_pose_capture_feedback(
            "right",
            {
                "face_count": 1,
                "valid": True,
                "yaw_degrees": 82.0,
                "eye_width_ratio": 0.5,
                "brightness": 120.0,
                "sharpness": 5.0,
                "face_ratio": 0.05,
            },
        )
        self.assertIn("Turned too far into full profile", feedback)

    def test_get_pose_capture_feedback_left_valid_angle_good_asymmetry(self):
        # Yaw in valid range AND eye asymmetry sufficient → None (accepted)
        feedback = get_pose_capture_feedback(
            "left",
            {
                "face_count": 1,
                "valid": True,
                "yaw_degrees": -45.0,
                "eye_width_ratio": 1.30,  # right eye clearly narrower
                "brightness": 120.0,
                "sharpness": 5.0,
                "face_ratio": 0.05,
            },
        )
        self.assertIsNone(feedback)

    def test_get_pose_capture_feedback_left_valid_angle_poor_asymmetry(self):
        # Yaw in range but eye ratio too symmetric → rejected with asymmetry guidance
        feedback = get_pose_capture_feedback(
            "left",
            {
                "face_count": 1,
                "valid": True,
                "yaw_degrees": -40.0,
                "eye_width_ratio": 1.05,  # barely any asymmetry
                "brightness": 120.0,
                "sharpness": 5.0,
                "face_ratio": 0.05,
            },
        )
        self.assertIsNotNone(feedback)
        self.assertIn("right ear", feedback)

    def test_get_pose_capture_feedback_left_profile_valid(self):
        # Full left profile: deep yaw + strong asymmetry
        feedback = get_pose_capture_feedback(
            "left_profile",
            {
                "face_count": 1,
                "valid": True,
                "yaw_degrees": -72.0,
                "eye_width_ratio": 1.60,
                "brightness": 120.0,
                "sharpness": 5.0,
                "face_ratio": 0.05,
            },
        )
        self.assertIsNone(feedback)


if __name__ == "__main__":
    unittest.main()
