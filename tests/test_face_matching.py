import unittest

import numpy as np

from src.pipelines.face_matching import match_face_embeddings


class MatchFaceEmbeddingsTests(unittest.TestCase):
    def setUp(self):
        self.model_data = {
            'embeddings': np.array([
                [0.0, 0.0],
                [1.0, 1.0],
                [2.0, 2.0],
            ]),
            'student_ids': [10, 20, 30],
        }

    def test_matches_only_students_enrolled_in_the_selected_subject(self):
        detected, matched_count = match_face_embeddings(
            [np.array([0.0, 0.0]), np.array([1.0, 1.0])],
            self.model_data,
            candidate_student_ids=[20],
        )

        self.assertEqual(detected, {20: True})
        self.assertEqual(matched_count, 1)

    def test_matches_multiple_faces_and_counts_each_observation(self):
        detected, matched_count = match_face_embeddings(
            [np.array([0.0, 0.0]), np.array([1.0, 1.0])],
            self.model_data,
            candidate_student_ids=[10, 20],
        )

        self.assertEqual(detected, {10: True, 20: True})
        self.assertEqual(matched_count, 2)

    def test_leaves_faces_unmatched_when_no_enrolled_profile_matches(self):
        detected, matched_count = match_face_embeddings(
            [np.array([8.0, 8.0])],
            self.model_data,
            candidate_student_ids=[10, 20],
        )

        self.assertEqual(detected, {})
        self.assertEqual(matched_count, 0)
