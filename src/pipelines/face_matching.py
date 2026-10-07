import numpy as np


FACE_MATCH_THRESHOLD = 0.6


def match_face_embeddings(encodings, model_data, candidate_student_ids=None):
    student_ids = model_data['student_ids']
    embeddings = model_data['embeddings']

    if candidate_student_ids is not None:
        allowed_student_ids = {int(student_id) for student_id in candidate_student_ids}
        candidate_indices = [
            index
            for index, student_id in enumerate(student_ids)
            if int(student_id) in allowed_student_ids
        ]
        student_ids = [student_ids[index] for index in candidate_indices]
        embeddings = embeddings[candidate_indices]

    detected_students = {}
    matched_face_count = 0
    for encoding in encodings:
        if not student_ids:
            continue

        distances = np.linalg.norm(embeddings - encoding, axis=1)
        best_index = int(np.argmin(distances))
        if distances[best_index] <= FACE_MATCH_THRESHOLD:
            detected_students[int(student_ids[best_index])] = True
            matched_face_count += 1

    return detected_students, matched_face_count
