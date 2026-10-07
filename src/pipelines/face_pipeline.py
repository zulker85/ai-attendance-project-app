

import dlib
import numpy as np
import face_recognition_models
from PIL import Image
import streamlit as st

from src.database.db import get_all_students
from src.pipelines.face_matching import FACE_MATCH_THRESHOLD, match_face_embeddings


@st.cache_resource
def load_dlib_models():
    detector = dlib.get_frontal_face_detector() 


    sp = dlib.shape_predictor(
        face_recognition_models.pose_predictor_model_location()
    )

    facerec = dlib.face_recognition_model_v1(
        face_recognition_models.face_recognition_model_location()
    )

    return detector, sp, facerec


def get_face_embeddings(image_np, expected_face_count=0):
    detector, sp, facerec = load_dlib_models()
    height, width = image_np.shape[:2]
    max_dimension = max(height, width)
    if max_dimension > 1600:
        scale = 1600 / max_dimension
        image_np = np.asarray(
            Image.fromarray(image_np).resize(
                (int(width * scale), int(height * scale)),
                Image.BOX,
            )
        )

    faces = detector(image_np, 1)
    if expected_face_count and len(faces) < expected_face_count:
        higher_resolution_faces = detector(image_np, 2)
        if len(higher_resolution_faces) > len(faces):
            faces = higher_resolution_faces

    encodings= []

    for face in faces:
        shape = sp(image_np, face)
        face_descriptor = facerec.compute_face_descriptor(image_np, shape, 0)

        encodings.append(np.array(face_descriptor))
    return encodings

@st.cache_resource(ttl=5)
def get_trained_model():
    students = get_all_students()

    if not students:
        return None

    embeddings = []
    student_ids = []
    students_by_id = {}

    for student in students:
        embedding = student.get('face_embedding')
        if embedding:
            student_id = student.get('student_id')
            embeddings.append(np.asarray(embedding, dtype=np.float64))
            student_ids.append(student_id)
            students_by_id[student_id] = student

    if not embeddings:
        return None

    return {
        'embeddings': np.vstack(embeddings),
        'student_ids': student_ids,
        'students_by_id': students_by_id,
    }


def train_classifier():
    get_trained_model.clear()
    model_data = get_trained_model()
    return bool(model_data)

def predict_attendance(
    class_image_np,
    candidate_student_ids=None,
    expected_face_count=0,
):
    encodings = get_face_embeddings(class_image_np, expected_face_count)
    model_data = get_trained_model()

    if not model_data:
        return {}, len(encodings), len(encodings)

    detected_student, matched_face_count = match_face_embeddings(
        encodings,
        model_data,
        candidate_student_ids,
    )
    return (
        detected_student,
        len(encodings),
        len(encodings) - matched_face_count,
    )


def identify_student(image_np):
    encodings = get_face_embeddings(image_np)
    if len(encodings) != 1:
        return None, len(encodings)

    model_data = get_trained_model()
    if not model_data:
        return None, len(encodings)

    encoding = encodings[0]
    distances = np.linalg.norm(model_data['embeddings'] - encoding, axis=1)
    best_index = int(np.argmin(distances))
    if distances[best_index] > FACE_MATCH_THRESHOLD:
        return None, len(encodings)

    student_id = model_data['student_ids'][best_index]
    return model_data['students_by_id'][student_id], len(encodings)
