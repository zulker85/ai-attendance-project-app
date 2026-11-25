

import logging

import dlib
import numpy as np
import face_recognition_models
from PIL import Image
import streamlit as st

from src.database.db import get_all_face_templates, get_all_students
from src.pipelines.face_matching import (
    FACE_MATCH_THRESHOLD,
    evaluate_face_match,
    evaluate_face_match_details,
    match_face_embeddings,
)


FACE_EMBEDDING_SIZE = 128
REQUIRED_FACE_POSES = ('front', 'left', 'right')
logger = logging.getLogger(__name__)


def missing_required_face_poses(captured_poses):
    captured_poses = set(captured_poses)
    return [pose for pose in REQUIRED_FACE_POSES if pose not in captured_poses]


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


@st.cache_resource
def load_cnn_detector():
    """CNN face detector — slower but detects profile/side faces reliably."""
    return dlib.cnn_face_detection_model_v1(
        face_recognition_models.cnn_face_detector_model_location()
    )


def _detect_faces_with_fallback(image_np, upsample=1):
    """Try frontal detector; fall back to CNN if no faces found (for profiles)."""
    detector, _, _ = load_dlib_models()
    faces = detector(image_np, upsample)
    if len(faces) == 0:
        cnn = load_cnn_detector()
        cnn_faces = cnn(image_np, upsample)
        faces = [f.rect for f in cnn_faces]
    return faces


def get_face_embeddings(image_np, expected_face_count=0):
    _, sp, facerec = load_dlib_models()
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

    faces = _detect_faces_with_fallback(image_np, upsample=1)
    if expected_face_count and len(faces) < expected_face_count:
        higher_resolution_faces = _detect_faces_with_fallback(image_np, upsample=2)
        if len(higher_resolution_faces) > len(faces):
            faces = higher_resolution_faces

    encodings= []

    for face in faces:
        shape = sp(image_np, face)
        face_descriptor = facerec.compute_face_descriptor(image_np, shape, 0)

        encodings.append(np.array(face_descriptor))
    return encodings


def detect_face_boxes(image_np):
    detector, _, _ = load_dlib_models()
    height, width = image_np.shape[:2]
    scale_x = scale_y = 1.0
    detection_image = image_np
    max_dimension = max(height, width)
    if max_dimension > 1600:
        detection_width = int(width * 1600 / max_dimension)
        detection_height = int(height * 1600 / max_dimension)
        detection_image = np.asarray(
            Image.fromarray(image_np).resize(
                (detection_width, detection_height),
                Image.BOX,
            )
        )
        scale_x = width / detection_width
        scale_y = height / detection_height

    boxes = []
    for face in detector(detection_image, 1):
        left = max(0, min(width, round(face.left() * scale_x)))
        top = max(0, min(height, round(face.top() * scale_y)))
        right = max(0, min(width, round(face.right() * scale_x)))
        bottom = max(0, min(height, round(face.bottom() * scale_y)))
        if right > left and bottom > top:
            boxes.append((left, top, right, bottom))
    return boxes


def estimate_face_orientation(shape):
    points = np.array([[shape.part(index).x, shape.part(index).y] for index in range(68)], dtype=np.float64)
    left_eye = points[36:42].mean(axis=0)
    right_eye = points[42:48].mean(axis=0)
    nose = points[30]
    eye_mid = (left_eye + right_eye) / 2.0
    eye_distance = max(float(np.linalg.norm(right_eye - left_eye)), 1.0)
    yaw = float(np.degrees(np.arctan2(nose[0] - eye_mid[0], eye_distance)))

    left_jaw_distance = float(np.linalg.norm(nose - points[0]))
    right_jaw_distance = float(np.linalg.norm(nose - points[16]))
    jaw_distance_ratio = (
        max(left_jaw_distance, right_jaw_distance)
        / max(min(left_jaw_distance, right_jaw_distance), 1.0)
    )

    # A frontal 68-point pose estimator can saturate poorly on a true profile.
    # The jaw/nose asymmetry is a useful fallback for the two profile poses.
    if jaw_distance_ratio >= 1.65:
        if right_jaw_distance < left_jaw_distance:
            label = 'left_profile'
        else:
            label = 'right_profile'
        return yaw, label

    # Approximate zones — no strict angles required:
    # left_profile / right_profile: past ~40° (ear starting to face camera)
    # left / right: any noticeable turn from 15° up to 80°
    # front: broadly centred (within 25°)
    if yaw < -80:
        label = 'left_profile'
    elif yaw < -40:
        label = 'left_profile'
    elif yaw < -15:
        label = 'left'
    elif yaw > 80:
        label = 'right_profile'
    elif yaw > 40:
        label = 'right_profile'
    elif yaw > 15:
        label = 'right'
    else:
        label = 'front'
    return yaw, label


def analyze_face_capture(image_np):
    _, sp, facerec = load_dlib_models()
    if image_np.ndim != 3 or image_np.shape[2] != 3:
        return None
    faces = _detect_faces_with_fallback(image_np, upsample=1)
    if len(faces) != 1:
        return {'face_count': len(faces), 'valid': False}

    face = faces[0]
    shape = sp(image_np, face)
    embedding = np.asarray(
        facerec.compute_face_descriptor(image_np, shape, 0),
        dtype=np.float64,
    )
    yaw, pose_label = estimate_face_orientation(shape)

    gray = np.asarray(
        Image.fromarray(image_np).convert("L"),
        dtype=np.float64,
    )
    left = max(0, min(gray.shape[1], face.left()))
    top = max(0, min(gray.shape[0], face.top()))
    right = max(left + 1, min(gray.shape[1], face.right()))
    bottom = max(top + 1, min(gray.shape[0], face.bottom()))
    face_gray = gray[top:bottom, left:right]
    brightness = float(face_gray.mean())
    gy, gx = np.gradient(face_gray)
    sharpness = float(np.sqrt(gx * gx + gy * gy).mean())
    face_width = max(face.right() - face.left(), 1)
    face_height = max(face.bottom() - face.top(), 1)
    face_ratio = ((face_width * face_height) / float(gray.shape[0] * gray.shape[1]))
    points = np.array(
        [[shape.part(index).x, shape.part(index).y] for index in range(68)],
        dtype=np.float64,
    )
    left_eye_width = float(np.ptp(points[36:42, 0]))
    right_eye_width = float(np.ptp(points[42:48, 0]))
    eye_width_ratio = (
        max(left_eye_width, right_eye_width)
        / max(min(left_eye_width, right_eye_width), 1.0)
    )

    quality_parts = [
        1.0 if 35 <= brightness <= 235 else max(0.0, 1.0 - abs(brightness - 135.0) / 135.0),
        1.0 if sharpness >= 4.0 else max(0.0, sharpness / 4.0),
        1.0 if face_ratio >= 0.01 else max(0.0, face_ratio / 0.01),
    ]
    quality_score = round(sum(quality_parts) / len(quality_parts), 3)

    valid = (
        brightness >= 30
        and sharpness >= 2.0
        and (
            face_ratio >= 0.008
            or (
                pose_label in {'left_profile', 'right_profile'}
                and face_ratio >= 0.005
            )
        )
    )
    return {
        'face_count': 1,
        'valid': bool(valid),
        'embedding': embedding,
        'pose_label': pose_label,
        'yaw_degrees': yaw,
        'quality_score': quality_score,
        'brightness': brightness,
        'sharpness': sharpness,
        'face_ratio': face_ratio,
        'eye_width_ratio': eye_width_ratio,
        'box': (int(left), int(top), int(right), int(bottom)),
        'image_shape': (int(gray.shape[0]), int(gray.shape[1])),
    }


def predict_attendance_details(
    class_image_np,
    candidate_student_ids=None,
    expected_face_count=0,
):
    detector, sp, facerec = load_dlib_models()
    height, width = class_image_np.shape[:2]
    max_dimension = max(height, width)
    image_np = class_image_np
    scale_x = scale_y = 1.0
    if max_dimension > 1600:
        scale = 1600 / max_dimension
        image_np = np.asarray(
            Image.fromarray(class_image_np).resize(
                (int(width * scale), int(height * scale)),
                Image.BOX,
            )
        )
        scale_x = width / image_np.shape[1]
        scale_y = height / image_np.shape[0]

    faces = detector(image_np, 1)
    if expected_face_count and len(faces) < expected_face_count:
        stronger_faces = detector(image_np, 2)
        if len(stronger_faces) > len(faces):
            faces = stronger_faces

    model_data = get_trained_model()
    observations = []
    recognized_ids = set()
    for face in faces:
        shape = sp(image_np, face)
        encoding = np.asarray(
            facerec.compute_face_descriptor(image_np, shape, 0),
            dtype=np.float64,
        )
        yaw, orientation = estimate_face_orientation(shape)
        box = (
            max(0, min(width, round(face.left() * scale_x))),
            max(0, min(height, round(face.top() * scale_y))),
            max(0, min(width, round(face.right() * scale_x))),
            max(0, min(height, round(face.bottom() * scale_y))),
        )
        student_id, distance, second_distance, reason, status, template_pose = (
            evaluate_face_match_details(
                encoding,
                model_data,
                candidate_student_ids,
            )
        )
        if status == 'recognized' and student_id is not None:
            if student_id in recognized_ids:
                status = 'borderline'
                reason = 'duplicate_detected_face_assignment'
                student_id = student_id
            else:
                recognized_ids.add(student_id)
        observations.append({
            'student_id': student_id,
            'distance': distance,
            'second_distance': second_distance,
            'rejection_reason': reason,
            'status': status,
            'orientation': orientation,
            'orientation_degrees': round(yaw, 1),
            'template_pose': template_pose,
            'box': box,
        })
    return observations


@st.cache_resource
def get_trained_model():
    students = get_all_students()
    templates = get_all_face_templates()

    if not students:
        return None

    students_by_id = {}
    duplicate_student_ids = set()
    for student in students:
        if not isinstance(student, dict):
            logger.warning("Skipping a face profile without a valid student row.")
            continue
        try:
            student_id = int(student.get('student_id'))
        except (TypeError, ValueError, OverflowError):
            logger.warning("Skipping a face profile with an invalid student ID.")
            continue
        if student_id <= 0:
            logger.warning("Skipping a face profile with an invalid student ID.")
            continue
        if student_id in students_by_id:
            duplicate_student_ids.add(student_id)
        else:
            students_by_id[student_id] = student

    for student_id in duplicate_student_ids:
        logger.error(
            "Excluding duplicate face profiles for student_id=%s.",
            student_id,
        )
        students_by_id.pop(student_id, None)

    embeddings = []
    student_ids = []
    pose_labels = {}
    valid_students_by_id = {}

    for student_id, student in students_by_id.items():
        if not isinstance(student.get('name'), str) or not student['name'].strip():
            logger.warning(
                "Skipping face profile without a valid name, student_id=%s.",
                student_id,
            )
            continue
        try:
            embedding = np.asarray(
                student.get('face_embedding'),
                dtype=np.float64,
            )
        except (TypeError, ValueError):
            logger.warning(
                "Skipping malformed face embedding, student_id=%s.",
                student_id,
            )
            continue
        if (
            embedding.shape != (FACE_EMBEDDING_SIZE,)
            or not np.isfinite(embedding).all()
        ):
            logger.warning(
                "Skipping invalid face embedding, student_id=%s.",
                student_id,
            )
            continue

        valid_student = dict(student)
        valid_student['student_id'] = student_id
        valid_students_by_id[student_id] = valid_student
        embeddings.append(embedding)
        student_ids.append(student_id)
        pose_labels[len(embeddings) - 1] = 'front'

    for template in templates:
        if not isinstance(template, dict):
            continue
        try:
            student_id = int(template.get('student_id'))
            embedding = np.asarray(template.get('embedding'), dtype=np.float64)
        except (TypeError, ValueError, OverflowError):
            continue
        if (
            student_id not in valid_students_by_id
            or embedding.shape != (FACE_EMBEDDING_SIZE,)
            or not np.isfinite(embedding).all()
        ):
            continue
        if template.get('model_version') not in (None, 'dlib-128-v1'):
            continue
        embedding_index = len(embeddings)
        embeddings.append(embedding)
        student_ids.append(student_id)
        pose_labels[embedding_index] = template.get('pose_label') or 'front'

    if not embeddings:
        return None

    return {
        'embeddings': np.vstack(embeddings),
        'student_ids': student_ids,
        'students_by_id': valid_students_by_id,
        'pose_labels': pose_labels,
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
        logger.info(
            "Face identification rejected rejection_reason=expected_one_face "
            "detected_face_count=%s",
            len(encodings),
        )
        return None, len(encodings)

    model_data = get_trained_model()
    if not model_data:
        evaluate_face_match(encodings[0], None)
        return None, len(encodings)

    student_id, _, _, _ = evaluate_face_match(encodings[0], model_data)
    if student_id is None:
        return None, len(encodings)

    student = model_data['students_by_id'].get(student_id)
    if student is None:
        logger.error(
            "Matched student_id=%s has no associated student record.",
            student_id,
        )
        return None, len(encodings)
    return student, len(encodings)


def measure_face_match(image_np, saved_embedding):
    encodings = get_face_embeddings(image_np)
    if len(encodings) != 1:
        logger.info(
            "Claimed face profile match rejected "
            "rejection_reason=expected_one_face detected_face_count=%s",
            len(encodings),
        )
        return None, len(encodings)

    try:
        saved_embedding = np.asarray(saved_embedding, dtype=np.float64)
    except (TypeError, ValueError):
        logger.warning("Rejecting malformed saved face embedding.")
        return None, len(encodings)
    if (
        saved_embedding.shape != (FACE_EMBEDDING_SIZE,)
        or not np.isfinite(saved_embedding).all()
    ):
        logger.warning("Rejecting invalid saved face embedding.")
        return None, len(encodings)

    distance = float(np.linalg.norm(saved_embedding - encodings[0]))
    rejection_reason = (
        'distance_above_threshold'
        if not np.isfinite(distance) or distance > FACE_MATCH_THRESHOLD
        else 'none'
    )
    logger.info(
        "Claimed face profile match rejection_reason=%s distance=%s "
        "threshold=%.3f",
        rejection_reason,
        f"{distance:.6f}" if np.isfinite(distance) else "unavailable",
        FACE_MATCH_THRESHOLD,
    )
    return distance, len(encodings)
